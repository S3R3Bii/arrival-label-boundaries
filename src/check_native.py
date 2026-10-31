"""Reconcile native BTS CSV through a separate parser and independent SQL classification."""
from pathlib import Path
from datetime import datetime
from fractions import Fraction
from collections import Counter
import argparse,csv,hashlib,json,re,sqlite3,zipfile
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def run(native):
    n=0
    def require(ok,label):
        nonlocal n
        assert ok,label;n+=1
    contract=json.loads((ROOT/'data/source_contract.json').read_bytes())
    capture=json.loads((ROOT/'data/capture_receipt.json').read_bytes())
    projection=json.loads((ROOT/'data/projection_receipt.json').read_bytes())
    require(hashlib.sha256(native.read_bytes()).hexdigest()==capture['sha256'],'native ZIP SHA256')
    db=sqlite3.connect(':memory:')
    db.execute('CREATE TABLE r(day TEXT,dest TEXT,carrier TEXT,code TEXT,key TEXT,can TEXT,div TEXT,kind TEXT,delay TEXT,ind TEXT)')
    def number(token):
        if not token:return '', 'MISSING'
        try:return str(Fraction(token)),'FINITE'
        except (ValueError,ZeroDivisionError):
            return '', 'NONFINITE' if re.fullmatch(r'[+-]?(?:s?nan\d*|inf(?:inity)?)',token,re.I) else 'INVALID'
    def binary(token):
        value,state=number(token)
        return str(int(Fraction(value))) if state=='FINITE' and Fraction(value) in [0,1] else 'MISSING' if state=='MISSING' else 'INVALID'
    national=selected=0
    with zipfile.ZipFile(native) as archive:
        for item in capture['members']:
            require(hashlib.sha256(archive.read(item['name'])).hexdigest()==item['sha256'],'native member SHA256')
        with archive.open(projection['member']) as stream:
            for chunk in pd.read_csv(stream,usecols=contract['selected_fields'],dtype=str,keep_default_na=False,chunksize=50000):
                national+=len(chunk)
                require(all(Fraction(x)==2024 for x in chunk['Year']),'independent native year')
                require(all(Fraction(x)==1 for x in chunk['Month']),'independent native month')
                subset=chunk[chunk['Dest'].isin(contract['destinations'])]
                insert=[]
                for row in subset.to_dict('records'):
                    row={k:v.strip() for k,v in row.items()}
                    token=row['FlightDate']
                    fmt='%Y-%m-%d' if '-' in token else '%Y%m%d'
                    day=datetime.strptime(token,fmt).strftime('%Y-%m-%d')
                    require(day.startswith('2024-01-'),'selected month')
                    parts=[day,*[row[k] for k in contract['identity_fields'][1:]]]
                    key=json.dumps(parts,separators=(',',':')) if all(parts) else ''
                    delay,kind=number(row['ArrDelay'])
                    insert.append((day,row['Dest'],row['DOT_ID_Reporting_Airline'] or 'MISSING',row['Reporting_Airline'],key,binary(row['Cancelled']),binary(row['Diverted']),kind,delay,binary(row['ArrDel15'])))
                db.executemany('INSERT INTO r VALUES (?,?,?,?,?,?,?,?,?,?)',insert);selected+=len(insert)
    db.execute('CREATE INDEX r_key_idx ON r(key)')
    query="""
    WITH counts AS(SELECT key,COUNT(*) AS n FROM r GROUP BY key),
    classified AS(
    SELECT r.*,CASE
    WHEN r.key='' THEN 'MISSING_KEY'
    WHEN counts.n!=1 THEN 'DUPLICATE_KEY'
    WHEN can NOT IN ('0','1') OR div NOT IN ('0','1') THEN 'UNKNOWN_OPERATION_FLAGS'
    WHEN can='1' AND div='1' THEN 'BOTH_OPERATION_FLAGS'
    WHEN can='1' THEN 'CANCELLED'
    WHEN div='1' THEN 'DIVERTED'
    WHEN kind!='FINITE' THEN 'UNKNOWN_DELAY'
    ELSE 'ELIGIBLE' END AS category
    FROM r JOIN counts USING(key))
    SELECT day,dest,carrier,code,category,can,div,kind,delay,ind,COUNT(*)
    FROM classified GROUP BY day,dest,carrier,code,category,can,div,kind,delay,ind
    """
    expected=Counter({tuple(row[:-1]):row[-1] for row in db.execute(query)})
    with (ROOT/'data/day_carrier_cells.csv').open(encoding='utf-8',newline='') as stream:cells=list(csv.DictReader(stream))
    observed=Counter()
    for cell in cells:
        value=cell['delay_token'];state=cell['delay_state']
        require(state in ['FINITE','MISSING','INVALID','NONFINITE'],'explicit source delay state')
        require(cell['destination'] in ['ORD','ATL'],'fixed destination')
        require(cell['official_indicator'] in ['0','1','MISSING','INVALID'],'source indicator state')
        require(int(cell['records'])>0,'positive sufficient cell count')
        key=(cell['day'],cell['destination'],cell['carrier_id'],cell['carrier_code'],cell['category'],cell['cancelled_flag'],cell['diverted_flag'],state,str(Fraction(value)) if state=='FINITE' else '',cell['official_indicator'])
        observed[key]+=int(cell['records'])
    require(observed==expected,'every native sufficient-cell key/count; independent SQL classification')
    require(national==projection['national_records'],'all national records')
    require(selected==projection['selected_records']==sum(observed.values()),'all selected records preserved')
    require({r[1] for r in expected}=={'ORD','ATL'},'both original destinations')
    catalog=json.loads((ROOT/'data/source_catalog.json').read_bytes())
    observed_codes={}
    for carrier,code in db.execute('SELECT DISTINCT carrier,code FROM r'):
        observed_codes.setdefault(carrier,set()).add(code)
    require({k:sorted(v) for k,v in observed_codes.items()}==catalog['carrier_codes'],'every native carrier code label')
    for name,digest in projection['files'].items():require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'producer-bound source bytes')
    receipt=dict(status='PASS',finite_conditions=n,national_records=national,selected_records=selected,sufficient_cells=len(cells),
        native_archive_sha256=capture['sha256'],pandas_version=pd.__version__,
        hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['data/day_carrier_cells.csv','data/source_catalog.json','data/capture_receipt.json','data/source_contract.json','data/projection_receipt.json']},
        methods='Independent pandas C CSV parser,exact Fraction tokens,SQLite key multiplicities and CASE classification;no production ingestion import.',
        scope='Complete current native-to-sufficient-count reconciliation;not original vintage,physical seconds,carrier quality or European label equivalence.')
    (ROOT/'data/native_verification.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps(receipt))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);run(p.parse_args().archive)
