"""Generate deterministic CER-AI educational tomography mock-ups.

These figures are deliberately schematic and must never be used as device
exports, patient records, or clinical inputs.
"""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch

matplotlib.rcParams["svg.fonttype"] = "none"


OUTPUT = Path(__file__).resolve().parents[1] / "static" / "education" / "pentacam-synthetic"
NOTICE = "CER-AI SYNTHETIC TRAINING DISPLAY — NOT A DEVICE EXPORT — NOT REAL PATIENT DATA"
NAVY = "#102f46"
BLUE = "#1b628f"
PALE = "#eaf2f7"
GRID = "#c8d7e1"
ORANGE = "#b76512"
GREEN = "#2d7650"


CASES = {
    "OD": {
        "state": "SUSPICIOUS TEACHING EYE",
        "k1": 43.8,
        "k1_axis": 10,
        "k2": 45.2,
        "k2_axis": 100,
        "kmax": 47.0,
        "pupil": 505,
        "thin": 492,
        "front_ele": 8,
        "back_ele": 17,
        "ppi_min": 0.91,
        "ppi_avg": 1.35,
        "ppi_max": 1.70,
        "artmax": 289,
        "df": 1.85,
        "db": 2.10,
        "dp": 1.95,
        "dt": 1.70,
        "da": 1.90,
        "final_d": 2.35,
        "is": 0.85,
        "offset": (0.28, -0.38),
    },
    "OS": {
        "state": "NORMAL TEACHING EYE",
        "k1": 43.5,
        "k1_axis": 5,
        "k2": 44.4,
        "k2_axis": 95,
        "kmax": 44.8,
        "pupil": 530,
        "thin": 524,
        "front_ele": 3,
        "back_ele": 8,
        "ppi_min": 0.82,
        "ppi_avg": 1.02,
        "ppi_max": 1.25,
        "artmax": 419,
        "df": 0.80,
        "db": 1.00,
        "dp": 0.70,
        "dt": 0.90,
        "da": 0.80,
        "final_d": 1.10,
        "is": 0.20,
        "offset": (0.08, -0.12),
    },
}


def grid(size: int = 240) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    axis = np.linspace(-1, 1, size)
    xx, yy = np.meshgrid(axis, axis)
    radius = np.sqrt(xx**2 + yy**2)
    return xx, yy, radius


def fields(case: dict[str, float | str | tuple[float, float]]) -> dict[str, np.ma.MaskedArray]:
    xx, yy, radius = grid()
    ox, oy = case["offset"]
    local = np.exp(-(((xx - ox) / 0.34) ** 2 + ((yy - oy) / 0.30) ** 2))
    bow_tie = np.cos(2 * np.arctan2(yy, xx)) * np.exp(-(radius / 0.78) ** 2)
    suspicious = case["state"].startswith("SUSPICIOUS")
    curvature = 43.7 + 0.85 * bow_tie + (2.35 if suspicious else 0.55) * local
    front = -2.0 + 3.0 * bow_tie + (10.0 if suspicious else 4.0) * local
    back = -3.0 + 4.0 * bow_tie + (21.0 if suspicious else 9.0) * local
    pachy = case["thin"] + 78 * radius**1.55 + (10 if suspicious else 5) * (
        (xx - ox) ** 2 + (yy - oy) ** 2
    )
    mask = radius > 1
    return {
        "curvature": np.ma.masked_where(mask, curvature),
        "front": np.ma.masked_where(mask, front),
        "back": np.ma.masked_where(mask, back),
        "pachy": np.ma.masked_where(mask, pachy),
    }


def style_map(ax: plt.Axes, title: str, field: np.ma.MaskedArray, cmap: str, vmin: float, vmax: float, unit: str) -> None:
    image = ax.imshow(field, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, extent=(-1, 1, -1, 1))
    ax.add_patch(Circle((0, 0), 1, fill=False, lw=1.2, color="#536775"))
    ax.axhline(0, color="white", lw=0.45, alpha=0.55)
    ax.axvline(0, color="white", lw=0.45, alpha=0.55)
    ax.set_title(title, fontsize=10.5, color=NAVY, weight="bold", pad=7)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = plt.colorbar(image, ax=ax, fraction=0.046, pad=0.025)
    bar.ax.tick_params(labelsize=7)
    bar.set_label(unit, fontsize=7)


def header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.04, 0.968, title, color=NAVY, fontsize=17, weight="bold", va="top")
    fig.text(0.04, 0.938, subtitle, color="#405a69", fontsize=9.5, va="top")
    fig.text(0.5, 0.012, NOTICE, ha="center", color="#9b2730", fontsize=8.2, weight="bold")


def watermark(fig: plt.Figure) -> None:
    fig.text(
        0.5,
        0.5,
        "SYNTHETIC",
        ha="center",
        va="center",
        rotation=28,
        fontsize=58,
        color="#9b2730",
        alpha=0.085,
        weight="bold",
    )


def save(fig: plt.Figure, filename: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT / Path(filename).with_suffix(".svg")
    buffer = io.StringIO()
    fig.savefig(buffer, format="svg", facecolor="white", bbox_inches="tight")
    ascii_svg = buffer.getvalue().encode("ascii", "xmlcharrefreplace").decode("ascii")
    destination.write_text(ascii_svg, encoding="ascii")
    plt.close(fig)


def four_maps(eye: str) -> None:
    case = CASES[eye]
    data = fields(case)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=False)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.875, bottom=0.10, wspace=0.18, hspace=0.25)
    header(fig, f"4 Maps Refractive — {eye}", f"{case['state']} · standard quadrant training layout")
    style_map(axes[0, 0], "UPPER LEFT · Axial/Sagittal Curvature (Front)", data["curvature"], "turbo", 39, 49, "D")
    style_map(axes[0, 1], "UPPER RIGHT · Elevation (Front)", data["front"], "RdYlBu_r", -15, 18, "µm")
    style_map(axes[1, 0], "LOWER LEFT · Corneal Thickness / Pachymetry", data["pachy"], "viridis", 480, 610, "µm")
    style_map(axes[1, 1], "LOWER RIGHT · Elevation (Back)", data["back"], "RdYlBu_r", -20, 30, "µm")
    ox, oy = case["offset"]
    axes[1, 0].plot(ox, oy, "o", ms=7, mec="black", mfc="none", mew=1.4)
    axes[1, 0].text(ox + 0.06, oy - 0.08, f"Thin {case['thin']} µm", fontsize=8, weight="bold")
    fig.text(
        0.5,
        0.06,
        f"K1 {case['k1']:.1f} D @ {case['k1_axis']}°   ·   K2 {case['k2']:.1f} D @ {case['k2_axis']}°   ·   "
        f"Kmax {case['kmax']:.1f} D   ·   Pupil Center {case['pupil']} µm   ·   Thinnest {case['thin']} µm",
        ha="center",
        fontsize=9.5,
        color=NAVY,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": PALE, "edgecolor": GRID},
    )
    watermark(fig)
    save(fig, f"four-maps-{eye.lower()}.png")


def bad_display(eye: str) -> None:
    case = CASES[eye]
    data = fields(case)
    fig = plt.figure(figsize=(13, 8.6))
    grid_spec = fig.add_gridspec(3, 4, left=0.045, right=0.96, top=0.86, bottom=0.17, wspace=0.24, hspace=0.35)
    header(fig, f"Belin/Ambrósio BAD Display — {eye}", f"{case['state']} · source-region teaching mock-up")
    style_map(fig.add_subplot(grid_spec[0, 0]), "Front elevation", data["front"], "RdYlBu_r", -15, 18, "µm")
    style_map(fig.add_subplot(grid_spec[0, 1]), "Enhanced front", data["front"] * 1.12, "RdYlBu_r", -15, 18, "µm")
    style_map(fig.add_subplot(grid_spec[1, 0]), "Back elevation", data["back"], "RdYlBu_r", -20, 30, "µm")
    style_map(fig.add_subplot(grid_spec[1, 1]), "Enhanced back", data["back"] * 1.12, "RdYlBu_r", -20, 30, "µm")
    style_map(fig.add_subplot(grid_spec[0:2, 2]), "Corneal thickness", data["pachy"], "viridis", 480, 610, "µm")

    profile = fig.add_subplot(grid_spec[0, 3])
    radius = np.linspace(0, 4, 80)
    patient = case["thin"] + (19 if eye == "OD" else 16) * radius**1.25
    reference = 525 + 16 * radius**1.25
    profile.plot(radius, reference, "--", color="#6e7f89", label="Reference")
    profile.plot(radius, patient, color=ORANGE if eye == "OD" else GREEN, lw=2.2, label=eye)
    profile.set_title("CTSP", color=NAVY, fontsize=10, weight="bold")
    profile.set_xlabel("Radius (mm)", fontsize=7)
    profile.set_ylabel("Thickness (µm)", fontsize=7)
    profile.tick_params(labelsize=7)
    profile.grid(alpha=0.2)
    profile.legend(fontsize=7, frameon=False)

    pti = fig.add_subplot(grid_spec[1, 3])
    pti_patient = (patient - case["thin"]) / case["thin"] * 100
    pti_ref = (reference - 525) / 525 * 100
    pti.plot(radius, pti_ref, "--", color="#6e7f89", label="Reference")
    pti.plot(radius, pti_patient, color=ORANGE if eye == "OD" else GREEN, lw=2.2, label=eye)
    pti.set_title("PTI", color=NAVY, fontsize=10, weight="bold")
    pti.set_xlabel("Radius (mm)", fontsize=7)
    pti.set_ylabel("Increase (%)", fontsize=7)
    pti.tick_params(labelsize=7)
    pti.grid(alpha=0.2)

    metrics = fig.add_subplot(grid_spec[2, :])
    metrics.axis("off")
    entries = [
        ("F.Ele.Th", f"{case['front_ele']:+.0f} µm"),
        ("B.Ele.Th", f"{case['back_ele']:+.0f} µm"),
        ("PPI Min / Avg / Max", f"{case['ppi_min']:.2f} / {case['ppi_avg']:.2f} / {case['ppi_max']:.2f}"),
        ("ARTmax", f"{case['artmax']:.0f}"),
        ("Df", f"{case['df']:.2f}"),
        ("Db", f"{case['db']:.2f}"),
        ("Dp", f"{case['dp']:.2f}"),
        ("Dt", f"{case['dt']:.2f}"),
        ("Da", f"{case['da']:.2f}"),
        ("Final D", f"{case['final_d']:.2f}"),
    ]
    for index, (label, value) in enumerate(entries):
        x = 0.015 + (index % 5) * 0.197
        y = 0.60 if index < 5 else 0.08
        color = ORANGE if eye == "OD" and index >= 4 else NAVY
        box = FancyBboxPatch((x, y), 0.175, 0.32, boxstyle="round,pad=0.009", facecolor="#ffffff", edgecolor=GRID)
        metrics.add_patch(box)
        metrics.text(x + 0.012, y + 0.22, label, fontsize=7.5, color="#526775")
        metrics.text(x + 0.012, y + 0.07, value, fontsize=11, color=color, weight="bold")
    fig.text(0.5, 0.108, "Bottom D strip values are standardized deviations; elevation values remain separate signed µm measurements.", ha="center", fontsize=8.5, color="#405a69")
    watermark(fig)
    save(fig, f"bad-display-{eye.lower()}.png")


def topometric_show_two() -> None:
    fig = plt.figure(figsize=(14, 8.8))
    spec = fig.add_gridspec(2, 4, left=0.045, right=0.96, top=0.85, bottom=0.11, wspace=0.28, hspace=0.28)
    header(fig, "Show 2 Exams Topometric — OD / OS", "Bilateral source comparison · OD suspicious teaching eye, OS normal teaching eye")
    for row, eye in enumerate(("OD", "OS")):
        case = CASES[eye]
        data = fields(case)
        style_map(spec_ax := fig.add_subplot(spec[row, 0]), f"{eye} · Cornea Front", data["curvature"], "turbo", 39, 49, "D")
        style_map(fig.add_subplot(spec[row, 1]), f"{eye} · Cornea Back", data["back"], "RdYlBu_r", -20, 30, "µm")
        front = fig.add_subplot(spec[row, 2])
        front.axis("off")
        front.set_title(f"{eye} · Cornea Front table", fontsize=10.5, color=NAVY, weight="bold")
        astig = case["k2"] - case["k1"]
        table_rows = [
            ["K1", f"{case['k1']:.1f} D", f"Axis {case['k1_axis']}°"],
            ["K2", f"{case['k2']:.1f} D", f"Axis {case['k2_axis']}°"],
            ["Km", f"{(case['k1'] + case['k2']) / 2:.1f} D", "printed"],
            ["Astig", f"{astig:.1f} D", f"Steep {case['k2_axis']}°"],
            ["Back Km", f"{-6.2 if eye == 'OD' else -6.1:.1f} D", "source locked"],
            ["Back Rmin", f"{5.55 if eye == 'OD' else 5.62:.2f} mm", "source locked"],
        ]
        tbl = front.table(cellText=table_rows, colLabels=["Field", "Value", "Source note"], loc="center", cellLoc="left", colLoc="left")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8.3)
        tbl.scale(1, 1.45)
        for (r, _), cell in tbl.get_celld().items():
            cell.set_edgecolor(GRID)
            if r == 0:
                cell.set_facecolor(PALE)
                cell.set_text_props(weight="bold", color=NAVY)

        indices = fig.add_subplot(spec[row, 3])
        indices.axis("off")
        indices.set_title(f"{eye} · Center Indices (8 mm)", fontsize=10.5, color=NAVY, weight="bold")
        values = (
            [("ISV", "30"), ("IVA", "0.22"), ("KI", "1.05"), ("CKI", "1.01"), ("IHA", "10.0"), ("IHD", "0.018"), ("RMin", "7.25 mm"), ("TKC", "—"), ("KISA%", "30"), ("I-S", f"{case['is']:+.2f} D")]
            if eye == "OD"
            else [("ISV", "18"), ("IVA", "0.12"), ("KI", "1.02"), ("CKI", "1.00"), ("IHA", "5.2"), ("IHD", "0.010"), ("RMin", "7.55 mm"), ("TKC", "—"), ("KISA%", "12"), ("I-S", f"{case['is']:+.2f} D")]
        )
        idx_table = indices.table(cellText=values, colLabels=["Index", "Printed value"], loc="center", cellLoc="left", colLoc="left")
        idx_table.auto_set_font_size(False)
        idx_table.set_fontsize(8.3)
        idx_table.scale(1, 1.24)
        for (r, _), cell in idx_table.get_celld().items():
            cell.set_edgecolor(GRID)
            if r == 0:
                cell.set_facecolor(PALE)
                cell.set_text_props(weight="bold", color=NAVY)
        spec_ax.text(-0.88, 0.80, case["state"], fontsize=7.2, color=ORANGE if eye == "OD" else GREEN, weight="bold", bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "none"})
    watermark(fig)
    save(fig, "show-2-exams-topometric.png")


def main() -> None:
    four_maps("OD")
    four_maps("OS")
    bad_display("OD")
    bad_display("OS")
    topometric_show_two()


if __name__ == "__main__":
    main()
