"""Create complete source-bound recorded-label and denominator figures."""

from pathlib import Path
from fractions import Fraction
import csv, hashlib, json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    with (ROOT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "arrival-label-boundaries",
        }
    )
    accounts = read("results/airport_accounts.csv")
    days = read("results/daily_accounts.csv")
    folder = ROOT / "figures"
    folder.mkdir(exist_ok=True)
    manifest = []
    palette = ["#177f83", "#d18a22", "#5d59b1"]

    def finish(fig, name, items):
        fig.canvas.draw()
        width, height = fig.get_size_inches() * 72
        for item, ax in items:
            box = ax.get_position()
            item["axis_points"] = dict(
                left=float(box.x0 * width),
                top=float((1 - box.y1) * height),
                width=float(box.width * width),
                height=float(box.height * height),
                xlim=list(map(float, ax.get_xlim())),
                ylim=list(map(float, ax.get_ylim())),
            )
        for ext in ["png", "svg", "pdf"]:
            metadata = (
                {"Date": None}
                if ext == "svg"
                else {"CreationDate": None, "ModDate": None} if ext == "pdf" else None
            )
            fig.savefig(
                folder / (name + "." + ext),
                dpi=160,
                facecolor="white",
                metadata=metadata,
            )
        svg = folder / (name + ".svg")
        svg.write_bytes(
            (
                "\n".join(
                    x.rstrip() for x in svg.read_text(encoding="utf-8").splitlines()
                )
                + "\n"
            ).encode()
        )
        manifest.append(
            dict(
                name=name,
                artists=[r for r, ax in items],
                asset_sha256={
                    ext: hashlib.sha256(
                        (folder / (name + "." + ext)).read_bytes()
                    ).hexdigest()
                    for ext in ["png", "svg", "pdf"]
                },
            )
        )
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.subplots_adjust(left=0.11, right=0.93, top=0.79, bottom=0.18)
    fig.suptitle(
        "A one-minute cutoff change alters the recorded target",
        fontsize=15,
        x=0.11,
        ha="left",
        y=0.97,
    )
    fig.text(
        0.11,
        0.88,
        "Completed nondiverted source records; percentages use the fixed eligible denominator",
        fontsize=10,
    )
    items = []
    for j, cutoff in enumerate([14, 15, 16]):
        x = np.arange(2) + (j - 1) * 0.24
        values = [float(Fraction(r["rate_ge" + str(cutoff)]) * 100) for r in accounts]
        bars = ax.bar(
            x,
            values,
            width=0.24,
            color=palette[j],
            label=">= " + str(cutoff) + " minutes",
        )
        for bar, value, row, position in zip(bars, values, accounts, x):
            gid = "threshold-" + row["destination"] + "-" + str(cutoff)
            bar.set_gid(gid)
            label = format(value, ".2f") + "%"
            ax.text(position, value + 0.35, label, ha="center", fontsize=10)
            items.append(
                (
                    dict(
                        gid=gid,
                        kind="threshold",
                        destination=row["destination"],
                        cutoff=cutoff,
                        value=float(value),
                        position=float(position),
                        thickness=0.24,
                        label=label,
                        orientation="vertical",
                    ),
                    ax,
                )
            )
    ax.set_xticks(
        [0, 1],
        [
            r["destination"] + "\nEligible n=" + format(int(r["eligible_records"]), ",")
            for r in accounts
        ],
    )
    ax.set_ylim(0, 35)
    ax.set_ylabel("Percent of eligible source records")
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.11))
    fig.text(
        0.11,
        0.025,
        "One January 2024 source view. These probes do not identify physical seconds or European OTP15.",
        fontsize=9,
    )
    finish(fig, "threshold_rates", items)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.5))
    fig.subplots_adjust(left=0.09, right=0.94, top=0.85, bottom=0.13, hspace=0.48)
    fig.suptitle(
        "The boundary-bin share varies across the fixed days",
        fontsize=15,
        x=0.09,
        ha="left",
        y=0.97,
    )
    fig.text(
        0.09,
        0.91,
        "All 31 days at both airports; source values from 15 inclusive to 16 exclusive minutes",
        fontsize=10,
    )
    items = []
    maximum = max(float(Fraction(r["boundary_fraction"]) * 100) for r in days)
    for j, destination in enumerate(["ORD", "ATL"]):
        ax = axes[j]
        rows = [r for r in days if r["destination"] == destination]
        values = [
            (
                float(Fraction(r["boundary_fraction"]) * 100)
                if r["boundary_fraction"]
                else 0
            )
            for r in rows
        ]
        x = np.arange(31)
        bars = ax.bar(x, values, width=0.72, color=palette[j])
        ax.set_title(destination, loc="left", fontsize=11)
        ax.set_xticks(x, [r["day"][-2:] for r in rows], fontsize=9)
        ax.set_ylim(0, maximum * 1.28)
        ax.set_ylabel("Percent of eligible records")
        ax.set_xlabel("January 2024 source flight day")
        ax.grid(axis="y", alpha=0.18)
        ax.set_axisbelow(True)
        for bar, value, row, position in zip(bars, values, rows, x):
            gid = "daily-" + destination + "-" + row["day"]
            bar.set_gid(gid)
            items.append(
                (
                    dict(
                        gid=gid,
                        kind="daily",
                        destination=destination,
                        day=row["day"],
                        value=float(value),
                        position=float(position),
                        thickness=0.72,
                        orientation="vertical",
                    ),
                    ax,
                )
            )
    fig.text(
        0.09,
        0.025,
        "No day is omitted. Daily eligibility counts and exact ratios are retained; no carrier/airport quality ranking.",
        fontsize=9,
    )
    finish(fig, "daily_boundary", items)
    fields = [
        "missing_key_records",
        "duplicate_key_records",
        "unknown_operation_flag_records",
        "both_operation_flags_records",
        "cancelled_records",
        "diverted_records",
        "unknown_delay_records",
        "eligible_records",
    ]
    labels = [
        "Missing key",
        "Duplicate key",
        "Unknown flags",
        "Both flags set",
        "Cancelled",
        "Diverted",
        "Unknown delay",
        "Eligible",
    ]
    diagnostic_fields = [
        "official_indicator_known",
        "official_indicator_unknown",
        "official_indicator_mismatch",
    ]
    diagnostic_labels = ["Usable indicator", "Unknown indicator", "Mismatch"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 6.5), gridspec_kw={"wspace": 0.58})
    fig.subplots_adjust(left=0.16, right=0.94, top=0.81, bottom=0.14)
    fig.suptitle(
        "Denominators retain cancellations, diversions and unknowns",
        fontsize=15,
        x=0.07,
        ha="left",
        y=0.97,
    )
    fig.text(
        0.07,
        0.90,
        "Left: complete source eligibility partition. Right: eligible-record indicator diagnostics, which can overlap.",
        fontsize=9.5,
    )
    items = []
    for panel, (names, texts) in enumerate(
        [(fields, labels), (diagnostic_fields, diagnostic_labels)]
    ):
        ax = axes[panel]
        maximum = max(int(r[f]) for r in accounts for f in names)
        for j, row in enumerate(accounts):
            y = np.arange(len(names)) + (j - 0.5) * 0.32
            values = [int(row[f]) for f in names]
            bars = ax.barh(
                y, values, height=0.32, color=palette[j], label=row["destination"]
            )
            for bar, value, field, position in zip(bars, values, names, y):
                gid = "source-" + row["destination"] + "-" + field
                bar.set_gid(gid)
                label = format(value, ",")
                ax.text(
                    value + maximum * 0.018, position, label, va="center", fontsize=9
                )
                items.append(
                    (
                        dict(
                            gid=gid,
                            kind="source",
                            destination=row["destination"],
                            field=field,
                            value=float(value),
                            position=float(position),
                            thickness=0.32,
                            label=label,
                            orientation="horizontal",
                        ),
                        ax,
                    )
                )
        ax.set_yticks(np.arange(len(names)), texts)
        ax.invert_yaxis()
        ax.set_xlim(0, maximum * 1.26)
        ax.set_xlabel("Current source-record count")
        ax.grid(axis="x", alpha=0.18)
        ax.set_axisbelow(True)
        ax.legend(frameon=False, loc="upper right" if panel == 0 else "lower right")
    fig.text(
        0.07,
        0.025,
        "Zero categories remain visible as numeric labels. Source-indicator agreement is not proof of physical-second timing.",
        fontsize=9,
    )
    finish(fig, "source_denominators", items)
    (folder / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2) + "\n").encode()
    )
    print("FIGURES_PRODUCED", len(manifest), sum(len(r["artists"]) for r in manifest))


if __name__ == "__main__":
    main()
