"""Independently bind all actual SVG bars to complete recorded-label source results."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json, re, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    n = 0
    coordinates = 0

    def require(ok, label):
        nonlocal n
        assert ok, label
        n += 1

    accounts = {r["destination"]: r for r in read("results/airport_accounts.csv")}
    days = {(r["destination"], r["day"]): r for r in read("results/daily_accounts.csv")}
    figures = json.loads((ROOT / "figures/manifest.json").read_bytes())
    seen = set()
    require(len(figures) == 3, "three declared figures")
    for fig in figures:
        tree = ET.fromstring((ROOT / "figures" / (fig["name"] + ".svg")).read_bytes())
        groups = {r.attrib.get("id"): r for r in tree.iter() if r.tag.endswith("g")}
        texts = [
            "".join(r.itertext()).strip() for r in tree.iter() if r.tag.endswith("text")
        ]
        for ext, digest in fig["asset_sha256"].items():
            require(
                hashlib.sha256(
                    (ROOT / "figures" / (fig["name"] + "." + ext)).read_bytes()
                ).hexdigest()
                == digest,
                "current asset SHA256",
            )
        for item in fig["artists"]:
            gid = item["gid"]
            require(gid not in seen, "unique SVG source bar")
            seen.add(gid)
            if item["kind"] == "threshold":
                value = (
                    Fraction(
                        accounts[item["destination"]]["rate_ge" + str(item["cutoff"])]
                    )
                    * 100
                )
                require(
                    "Eligible n="
                    + format(
                        int(accounts[item["destination"]]["eligible_records"]), ","
                    )
                    in " ".join(texts),
                    "visible actual denominator",
                )
            elif item["kind"] == "daily":
                value = (
                    Fraction(
                        days[(item["destination"], item["day"])]["boundary_fraction"]
                    )
                    * 100
                )
            else:
                value = Fraction(accounts[item["destination"]][item["field"]])
            require(
                abs(float(value) - item["value"]) < 1e-12, "independent source value"
            )
            if "label" in item:
                require(item["label"] in texts, "actual SVG numeric label")
            paths = [x for x in groups[gid].iter() if x.tag.endswith("path")]
            require(len(paths) == 1, "actual bar path")
            numbers = list(
                map(
                    float,
                    re.findall(
                        r"[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?", paths[0].attrib["d"]
                    ),
                )
            )
            require(len(numbers) == 8, "four source-bar corners")
            xs = numbers[::2]
            ys = numbers[1::2]
            a = item["axis_points"]
            lo, hi = a["xlim"]
            bottom, top = a["ylim"]
            x = lambda v: a["left"] + (v - lo) / (hi - lo) * a["width"]
            y = lambda v: a["top"] + (top - v) / (top - bottom) * a["height"]
            if item["orientation"] == "vertical":
                expected_x = [
                    x(item["position"] - item["thickness"] / 2),
                    x(item["position"] + item["thickness"] / 2),
                ]
                expected_y = [y(0), y(float(value))]
            else:
                expected_x = [x(0), x(float(value))]
                expected_y = [
                    y(item["position"] - item["thickness"] / 2),
                    y(item["position"] + item["thickness"] / 2),
                ]
            for actual, target in [
                (min(xs), min(expected_x)),
                (max(xs), max(expected_x)),
                (min(ys), min(expected_y)),
                (max(ys), max(expected_y)),
            ]:
                require(abs(actual - target) < 0.02, "actual SVG source geometry")
                coordinates += 1
        if fig["name"] == "daily_boundary":
            require(
                all(str(i).zfill(2) in texts for i in range(1, 32)),
                "all fixed daily labels visible",
            )
    require(len(seen) == 90, "all6 threshold,62 daily and22 source bars")
    receipt = dict(
        status="PASS",
        finite_conditions=n,
        source_bound_artists=len(seen),
        svg_coordinate_conditions=coordinates,
        asset_hashes=9,
        scope="Actual SVG bars,denominator labels,complete source values/positions,all fixed days and asset hashes;visual review separate,no physical-second or accessibility certification.",
    )
    (ROOT / "figures/verification.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
