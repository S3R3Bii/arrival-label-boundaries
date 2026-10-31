"""Retain every selected BTS record in minimal exact sufficient-count cells."""
from pathlib import Path
from datetime import datetime
from decimal import Decimal,InvalidOperation
from collections import Counter,defaultdict
import argparse,csv,hashlib,io,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1]
def day(value):
    if not isinstance(value,str):return None
    for pattern,fmt in [(r'\d{4}-\d{2}-\d{2}','%Y-%m-%d'),(r'\d{8}','%Y%m%d')]:
        if re.fullmatch(pattern,value):
            try:return datetime.strptime(value,fmt).date().isoformat()
            except ValueError:return None
    return None
def numeric(value):
    token=value.strip() if isinstance(value,str) else ''
    if not token:return '', 'MISSING'
    try:parsed=Decimal(token)
    except InvalidOperation:return '', 'INVALID'
    if not parsed.is_finite():return '', 'NONFINITE'
    return str(parsed),'FINITE'
def flag(value):
    token,status=numeric(value)
    if status=='MISSING':return 'MISSING'
    if status=='FINITE' and Decimal(token) in [0,1]:return str(int(Decimal(token)))
    return 'INVALID'
def classify(key_valid,key_count,cancelled,diverted,delay_state):
    if not key_valid:return 'MISSING_KEY'
    if key_count!=1:return 'DUPLICATE_KEY'
    if cancelled not in ['0','1'] or diverted not in ['0','1']:return 'UNKNOWN_OPERATION_FLAGS'
    if cancelled==diverted=='1':return 'BOTH_OPERATION_FLAGS'
    if cancelled=='1':return 'CANCELLED'
    if diverted=='1':return 'DIVERTED'
    if delay_state!='FINITE':return 'UNKNOWN_DELAY'
    return 'ELIGIBLE'
def run(native):
    contract=json.loads((ROOT/'data/source_contract.json').read_bytes());receipt=json.loads((ROOT/'data/capture_receipt.json').read_bytes())
    raw=native.read_bytes();assert hashlib.sha256(raw).hexdigest()==receipt['sha256'] and len(raw)==receipt['bytes']
    selected=[];national=0;date_formats=Counter()
    with zipfile.ZipFile(native) as archive:
        members=[x for x in archive.namelist() if x.endswith('.csv') and 'On_Time_Reporting_Carrier_On_Time_Performance' in x]
        assert len(members)==1,'one intended data CSV'
        member=members[0]
        with archive.open(member) as binary,io.TextIOWrapper(binary,encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream);headers=reader.fieldnames
            assert all(k in headers for k in contract['selected_fields']),'fixed schema'
            for row in reader:
                national+=1
                assert Decimal(row['Year'])==2024 and Decimal(row['Month'])==1,'native month assertions'
                source_day=day(row['FlightDate']);assert source_day is not None and source_day.startswith('2024-01-'),'fixed native flight month'
                if row['Dest'] not in contract['destinations']:continue
                date_formats['ISO' if '-' in row['FlightDate'] else 'COMPACT']+=1
                row={k:row[k].strip() for k in contract['selected_fields']};row['normalized_day']=source_day
                row['key']=tuple([source_day,*[row[k] for k in contract['identity_fields'][1:]]])
                selected.append(row)
    assert selected and {r['Dest'] for r in selected}==set(contract['destinations']),'both fixed airports'
    keys=Counter(r['key'] for r in selected if all(r['key']))
    cells=Counter();codes=defaultdict(set);airport_ids=defaultdict(set)
    for row in selected:
        delay,state=numeric(row['ArrDelay']);cancelled=flag(row['Cancelled']);diverted=flag(row['Diverted']);indicator=flag(row['ArrDel15'])
        category=classify(all(row['key']),keys[row['key']],cancelled,diverted,state)
        carrier=row['DOT_ID_Reporting_Airline'] or 'MISSING'
        codes[carrier].add(row['Reporting_Airline'])
        if row['DestAirportID']:airport_ids[row['Dest']].add(row['DestAirportID'])
        cells[(row['normalized_day'],row['Dest'],carrier,row['Reporting_Airline'],category,cancelled,diverted,state,delay,indicator)]+=1
    assert all(len(v)==1 for v in airport_ids.values()),'source code/airport-ID ambiguity'
    fields=['day','destination','carrier_id','carrier_code','category','cancelled_flag','diverted_flag','delay_state','delay_token','official_indicator','records']
    target=ROOT/'data/day_carrier_cells.csv'
    with target.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(fields)
        for key,count in sorted(cells.items()):writer.writerow([*key,count])
    catalog=dict(carrier_codes={k:sorted(v) for k,v in sorted(codes.items())},destination_ids={k:sorted(v) for k,v in sorted(airport_ids.items())})
    (ROOT/'data/source_catalog.json').write_bytes((json.dumps(catalog,indent=2)+'\n').encode())
    projection=dict(status='PROJECTION_PRODUCED_NOT_YET_INDEPENDENTLY_VERIFIED',national_records=national,selected_records=len(selected),sufficient_cells=len(cells),member=member,headers=headers,date_token_formats=dict(date_formats),
                    files={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['data/day_carrier_cells.csv','data/source_catalog.json','data/capture_receipt.json','data/source_contract.json']},
                    scope='Minimal complete selected record counts,source eligibility and exact recorded-minute values;no tail numbers or flight-level identifiers published.')
    (ROOT/'data/projection_receipt.json').write_bytes((json.dumps(projection,indent=2)+'\n').encode());print(json.dumps(projection))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);run(p.parse_args().archive)
