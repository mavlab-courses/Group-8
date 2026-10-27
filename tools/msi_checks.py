"""Format and consistency checks of an OE3035 MSI project submission.

This module is PUBLIC: it is copied into the student template (tools/) and into
the Classroom 50 autograder bundle, both of which students can read. It must
never contain reference results. Everything it checks follows from the project
chapter alone: the file formats, the list of cases, the speeds and dimensions of
the hulls (published in the chapter), and the formulas of the MSI model.

Standard library only, Python 3.8 or later.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import re
from statistics import NormalDist

HERE = os.path.dirname(os.path.abspath(__file__))
G = 9.80665
HEADINGS = [90, 135, 180]
FN_RATIOS = [0.90, 0.95, 1.00, 1.05, 1.10]
FACTORS = ["0p900", "0p950", "1p050", "1p100"]
ZETA_V = 0.05
MAX_FILE_BYTES = 256 * 1024

FILES = {
    "cases": "results/msi_cases.csv",
    "roll": "results/roll_damping.csv",
    "sensitivity": "results/sensitivity.csv",
    "spikes": "results/spikes.csv",
}
COLUMNS = {
    "cases": ["hull", "beta_deg", "fn_ratio", "U_mps", "sigma_a", "abar", "we_bar", "mu_msi", "msi_pct"],
    "roll": ["hull", "omega_n", "zeta_wave", "Bv44"],
    "sensitivity": ["study", "hull", "beta_deg", "fn_ratio", "x_P_m", "y_P_m", "zeta_v",
                    "sigma_a", "abar", "we_bar", "mu_msi", "msi_pct"],
    "spikes": ["hull", "beta_deg", "fn_ratio", "omega"],
}
TEXT_COLUMNS = {"hull", "study"}
REQUIRED = ["cases", "roll", "sensitivity"]

# The parameter studies of the discussion (Deliverable 5d and 5e): the heading each
# must be run at, and how it changes the cabin position or the roll damping.
STUDIES = {
    "cabin_midship":    dict(beta=180, x=0.0, y=1.0, zeta=ZETA_V, text="head seas, cabin at midship (x_P = 0)"),
    "cabin_centreline": dict(beta=90, x=1.0, y=0.0, zeta=ZETA_V, text="beam seas, cabin on the centreline (y_P = 0)"),
    "cabin_starboard":  dict(beta=90, x=1.0, y=-1.0, zeta=ZETA_V, text="beam seas, cabin to starboard (y_P = -0.4B)"),
    "damping_low":      dict(beta=90, x=1.0, y=1.0, zeta=0.025, text="beam seas, zeta_v = 0.025"),
    "damping_high":     dict(beta=90, x=1.0, y=1.0, zeta=0.10, text="beam seas, zeta_v = 0.10"),
}
# x and y above multiply the project cabin position (x_P, y_P) of the hull.

_NAME_OK = re.compile(r"^[A-Za-z0-9_.+-]{1,32}$")


def load_members():
    """Published particulars of the 25 hulls: Lpp, B, T, speeds, cabin position."""
    with open(os.path.join(HERE, "members.json")) as fh:
        return json.load(fh)


def safe(text):
    """A student-supplied name, fit to be echoed in a report (no markup, no @mentions)."""
    text = str(text).strip()
    return f"`{text}`" if _NAME_OK.match(text) else "(unreadable name)"


def msi_model(abar, we_bar):
    """O'Hanlon & McCauley MSI (%) in 2 h, and mu_MSI."""
    mu = -0.819 + 2.32 * math.log10(we_bar) ** 2
    return 100 * NormalDist().cdf((math.log10(abar / G) - mu) / 0.4), mu


# ---------------------------------------------------------------- reading

class Table:
    def __init__(self, key):
        self.key, self.path = key, FILES[key]
        self.present = False
        self.rows = []            # dicts with a "_line" entry
        self.problems = []        # messages that make the file unusable or rows unusable


def parse_table(key, text):
    """Parse one result file. Blank lines and lines starting with # are skipped."""
    t = Table(key)
    if text is None:
        return t
    t.present = True
    if len(text.encode("utf-8", "replace")) > MAX_FILE_BYTES:
        t.problems.append(f"`{t.path}` is larger than {MAX_FILE_BYTES // 1024} kB.")
        return t
    lines = [(n, ln) for n, ln in enumerate(text.lstrip("﻿").splitlines(), 1)
             if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        t.problems.append(f"`{t.path}` has no header line.")
        return t
    reader = csv.reader(io.StringIO("\n".join(ln for _, ln in lines)))
    header = [h.strip().lower() for h in next(reader)]
    want = COLUMNS[key]
    missing = [c for c in want if c.lower() not in header]
    if missing:
        t.problems.append(f"`{t.path}` lacks the column(s) {', '.join('`%s`' % c for c in missing)}; "
                          f"the header must be `{','.join(want)}`.")
        return t
    idx = {c: header.index(c.lower()) for c in want}
    for (n, _), cells in zip(lines[1:], reader):
        row, bad = {"_line": n}, []
        for c in want:
            v = cells[idx[c]].strip() if idx[c] < len(cells) else ""
            if c in TEXT_COLUMNS:
                row[c] = v
                continue
            try:
                x = float(v)
                if not math.isfinite(x):
                    raise ValueError
                row[c] = x
            except ValueError:
                bad.append(c)
        if bad:
            t.problems.append(f"`{t.path}` line {n}: {', '.join('`%s`' % c for c in bad)} is not a finite number.")
        else:
            t.rows.append(row)
    return t


def snap(value, grid, tol):
    """The index of the grid value within tol of value, or None."""
    for i, g in enumerate(grid):
        if abs(value - g) <= tol:
            return i
    return None


class Submission:
    """The parsed result files of one submission."""

    def __init__(self, read):
        """read(path) returns the text of a file of the submission, or None if it is absent."""
        self.tables = {k: parse_table(k, read(p)) for k, p in FILES.items()}
        self.members = load_members()
        self.baseline, self.variant, self.hull_problems = self._identify()

    @property
    def cases(self):
        return self.tables["cases"]

    def hulls(self):
        return [h for h in (self.baseline, self.variant) if h]

    def _identify(self):
        names = []
        for r in self.cases.rows:
            if r["hull"] not in names:
                names.append(r["hull"])
        if not names:
            return None, None, ["No cases found, so your hulls are unknown."]
        unknown = [n for n in names if n not in self.members]
        if unknown:
            return None, None, [f"Unknown hull name(s) {', '.join(safe(n) for n in unknown)}. "
                                f"Use the member names of the HydRA results, e.g. `KCS_L1p000` and `KCS_L1p100`."]
        families = {n.split("_")[0] for n in names}
        base = [n for n in names if n.endswith("_L1p000")]
        var = [n for n in names if not n.endswith("_L1p000")]
        if len(families) != 1 or len(base) != 1 or len(var) != 1:
            return None, None, [f"Report exactly two hulls, your variant and its baseline (`<HULL>_L1p000`); "
                                f"found {', '.join(safe(n) for n in names)}."]
        return base[0], var[0], []

    def case_key(self, r):
        """(hull, beta index, speed index) of a row, or None if the heading or speed is not one of the project."""
        ib = snap(r["beta_deg"], HEADINGS, 0.5)
        iu = snap(r["fn_ratio"], FN_RATIOS, 0.005)
        if ib is None or iu is None or r["hull"] not in self.hulls():
            return None
        return r["hull"], ib, iu

    def case_map(self):
        """{(hull, ib, iu): row} of the first row of every valid case."""
        out = {}
        for r in self.cases.rows:
            k = self.case_key(r)
            if k and k not in out:
                out[k] = r
        return out

    def study_rows(self):
        """{study: [rows]} of the sensitivity rows whose study, hull, heading and speed are valid."""
        out = {s: [] for s in STUDIES}
        for r in self.tables["sensitivity"].rows:
            s = STUDIES.get(r["study"].strip().lower())
            if s is None or r["hull"] not in self.hulls():
                continue
            if snap(r["beta_deg"], HEADINGS, 0.5) is None or snap(r["fn_ratio"], FN_RATIOS, 0.005) is None:
                continue
            if abs(r["beta_deg"] - s["beta"]) > 0.5:
                continue
            out[r["study"].strip().lower()].append(r)
        return out


# ---------------------------------------------------------------- checks

class Check:
    def __init__(self, name, points):
        self.name, self.points = name, points
        self.score, self.messages = 0, []

    @property
    def passed(self):
        return self.score == self.points

    def grant(self, fraction=1.0):
        self.score = int(math.floor(self.points * max(0.0, min(1.0, fraction)) + 1e-9))


def _limit(msgs, n=8):
    return msgs if len(msgs) <= n else msgs[:n] + [f"... and {len(msgs) - n} more."]


def check_files(sub):
    c = Check("Result files present and readable", 2)
    bad = 0
    for k in REQUIRED:
        t = sub.tables[k]
        if not t.present:
            c.messages.append(f"`{t.path}` is missing.")
            bad += 1
        elif t.problems:
            c.messages += t.problems
            bad += 1
        elif not t.rows:
            c.messages.append(f"`{t.path}` has a header but no rows.")
            bad += 1
    t = sub.tables["spikes"]
    if t.present and t.problems:
        c.messages += [m + " (spikes.csv is not scored, but please fix it)" for m in t.problems]
    c.grant(1.0 if bad == 0 else 0.0)
    c.messages = _limit(c.messages)
    return c


def check_hulls(sub):
    c = Check("Two hulls: your variant and its baseline", 2)
    if sub.hull_problems:
        c.messages += sub.hull_problems
    else:
        c.grant()
        c.messages.append(f"Hulls: {safe(sub.variant)} and its baseline {safe(sub.baseline)}.")
    return c


def check_coverage(sub):
    c = Check("All 30 cases reported, once each", 3)
    if not sub.hulls():
        c.messages.append("Skipped: the hulls are unknown.")
        return c
    seen, msgs = {}, []
    for r in sub.cases.rows:
        k = sub.case_key(r)
        if k is None:
            msgs.append(f"`{FILES['cases']}` line {r['_line']}: hull, heading or speed ratio is not one of the project "
                        f"(headings {HEADINGS} deg, Fn/Fn_des {FN_RATIOS}).")
        elif k in seen:
            msgs.append(f"`{FILES['cases']}` line {r['_line']}: repeats the case of line {seen[k]}.")
        else:
            seen[k] = r["_line"]
    missing = [(h, HEADINGS[ib], FN_RATIOS[iu]) for h in sub.hulls() for ib in range(3) for iu in range(5)
               if (h, ib, iu) not in seen]
    for h, b, f in missing:
        msgs.append(f"Missing: {safe(h)}, beta = {b} deg, Fn/Fn_des = {f:.2f}.")
    c.messages = _limit(msgs)
    c.grant(1.0 if not msgs else (0.5 if len(seen) >= 20 else 0.0))
    return c


def check_speeds(sub):
    c = Check("Speeds U match the HydRA results", 2)
    cm = sub.case_map()
    if not cm:
        c.messages.append("Skipped: no valid cases.")
        return c
    bad = []
    for (h, ib, iu), r in sorted(cm.items(), key=lambda kv: kv[1]["_line"]):
        U = sub.members[h]["speeds"][iu]
        if abs(r["U_mps"] - U) > max(0.01, 0.005 * U):
            bad.append(f"`{FILES['cases']}` line {r['_line']}: U = {r['U_mps']:.3f} m/s, but the HydRA results of "
                       f"{safe(h)} at Fn/Fn_des = {FN_RATIOS[iu]:.2f} are for U = {U:.4f} m/s.")
    c.messages = _limit(bad)
    c.grant(1.0 if not bad else 0.0)
    return c


def _stat_rows(sub):
    rows = [(FILES["cases"], r) for r in sub.case_map().values()]
    for rs in sub.study_rows().values():
        rows += [(FILES["sensitivity"], r) for r in rs]
    return sorted(rows, key=lambda pr: (pr[0], pr[1]["_line"]))


def check_abar(sub):
    c = Check("Mean absolute acceleration: abar = sqrt(2/pi) sigma_a", 2)
    rows = _stat_rows(sub)
    if not rows:
        c.messages.append("Skipped: no valid cases.")
        return c
    bad = [f"`{p}` line {r['_line']}: abar / sigma_a = {r['abar'] / r['sigma_a']:.4f}, expected sqrt(2/pi) = 0.7979."
           for p, r in rows if r["sigma_a"] > 0 and abs(r["abar"] / (math.sqrt(2 / math.pi) * r["sigma_a"]) - 1) > 0.002]
    bad += [f"`{p}` line {r['_line']}: sigma_a must be positive." for p, r in rows if r["sigma_a"] <= 0]
    c.messages = _limit(bad)
    c.grant(1.0 if not bad else 0.0)
    return c


def check_msi_model(sub):
    c = Check("mu_MSI and MSI follow from abar and we_bar (O'Hanlon & McCauley)", 3)
    rows = [(p, r) for p, r in _stat_rows(sub) if r["abar"] > 0 and r["we_bar"] > 0]
    if not rows:
        c.messages.append("Skipped: no valid cases with positive abar and we_bar.")
        return c
    bad, erf_like = [], 0
    for p, r in rows:
        msi, mu = msi_model(r["abar"], r["we_bar"])
        if abs(r["mu_msi"] - mu) > 0.005:
            bad.append(f"`{p}` line {r['_line']}: mu_MSI = {r['mu_msi']:.4f}, but your we_bar gives {mu:.4f}.")
        if abs(r["msi_pct"] - msi) > max(0.1, 0.01 * msi):
            bad.append(f"`{p}` line {r['_line']}: MSI = {r['msi_pct']:.3f} %, but your abar and we_bar give {msi:.3f} %.")
            z = (math.log10(r["abar"] / G) - mu) / 0.4
            if abs(r["msi_pct"] - 100 * math.erf(z)) < 0.5 or abs(r["msi_pct"] - 100 * (msi / 100 - 0.5)) < 0.5:
                erf_like += 1
    c.messages = _limit(bad)
    if erf_like:
        c.messages.append("Some of your MSI values look like erf(z) or Phi(z) - 0.5 instead of Phi(z): see the warning "
                          "\"The error function is not Phi\" in the project chapter.")
    c.grant(1.0 if not bad else 0.0)
    return c


def check_plausible(sub):
    c = Check("Values in a physically plausible range", 1)
    rows = _stat_rows(sub)
    if not rows:
        c.messages.append("Skipped: no valid cases.")
        return c
    bad = []
    for p, r in rows:
        if not 0.1 < r["we_bar"] < 3.0:
            bad.append(f"`{p}` line {r['_line']}: we_bar = {r['we_bar']:.3f} rad/s is outside 0.1 to 3 rad/s "
                       f"(is it in rad/s, not Hz?).")
        if not 0 <= r["msi_pct"] <= 100:
            bad.append(f"`{p}` line {r['_line']}: MSI = {r['msi_pct']:.3f} is not a percentage.")
        if not 0 < r["sigma_a"] < 20:
            bad.append(f"`{p}` line {r['_line']}: sigma_a = {r['sigma_a']:.3f} m/s^2 is implausible.")
    c.messages = _limit(bad)
    c.grant(1.0 if not bad else 0.0)
    return c


def check_roll(sub):
    c = Check("Roll damping reported for both hulls", 2)
    t = sub.tables["roll"]
    if not sub.hulls():
        c.messages.append("Skipped: the hulls are unknown.")
        return c
    by = {}
    msgs = []
    for r in t.rows:
        if r["hull"] not in sub.hulls():
            msgs.append(f"`{t.path}` line {r['_line']}: {safe(r['hull'])} is not one of your two hulls.")
        elif r["hull"] in by:
            msgs.append(f"`{t.path}` line {r['_line']}: {safe(r['hull'])} appears twice.")
        else:
            by[r["hull"]] = r
    for h in sub.hulls():
        r = by.get(h)
        if r is None:
            msgs.append(f"`{t.path}`: no row for {safe(h)}.")
            continue
        if not 0.05 < r["omega_n"] < 2.0:
            msgs.append(f"`{t.path}` line {r['_line']}: omega_n = {r['omega_n']:.4g} rad/s is implausible.")
        if r["Bv44"] <= 0:
            msgs.append(f"`{t.path}` line {r['_line']}: Bv44 must be positive (in N m s).")
        if not abs(r["zeta_wave"]) < 1:
            msgs.append(f"`{t.path}` line {r['_line']}: zeta_wave is a fraction of critical damping.")
    c.messages = _limit(msgs)
    c.grant(1.0 if not msgs else 0.0)
    return c


def check_studies(sub):
    c = Check("Parameter studies: cabin position and roll damping", 2)
    t = sub.tables["sensitivity"]
    if not sub.hulls():
        c.messages.append("Skipped: the hulls are unknown.")
        return c
    msgs, done = [], 0
    valid = sub.study_rows()
    for r in t.rows:
        if not any(r is v for rs in valid.values() for v in rs):
            s = STUDIES.get(r["study"].strip().lower())
            why = (f"unknown study {safe(r['study'])} (use one of {', '.join(STUDIES)})" if s is None
                   else f"must be {s['text']}, for one of your hulls, at a speed of the project")
            msgs.append(f"`{t.path}` line {r['_line']}: {why}.")
    for name, s in STUDIES.items():
        rows = valid[name]
        if not rows:
            msgs.append(f"No row for `{name}` ({s['text']}).")
            continue
        ok = True
        for r in rows:
            m = sub.members[r["hull"]]
            want = (s["x"] * m["x_P"], s["y"] * m["y_P"], s["zeta"])
            got = (r["x_P_m"], r["y_P_m"], r["zeta_v"])
            for lab, w, g, tol in zip(("x_P_m", "y_P_m", "zeta_v"), want, got, (0.05, 0.05, 1e-4)):
                if abs(g - w) > max(tol, 0.005 * abs(w)):
                    msgs.append(f"`{t.path}` line {r['_line']}: `{name}` needs {lab} = {w:.4g}, not {g:.4g}.")
                    ok = False
        done += ok
    c.messages = _limit(msgs)
    c.grant(1.0 if not msgs else (0.5 if done >= 3 else 0.0))
    return c


def check_report(listdir):
    c = Check("Report committed as report/*.pdf", 1)
    names = listdir("report") or []
    if any(n.lower().endswith(".pdf") for n in names):
        c.grant()
    else:
        c.messages.append("No PDF in `report/` yet.")
    return c


def run_checks(sub, listdir=None):
    """All public checks. listdir(path) lists a folder of the submission (None skips the report check)."""
    checks = [check_files(sub), check_hulls(sub), check_coverage(sub), check_speeds(sub), check_abar(sub),
              check_msi_model(sub), check_plausible(sub), check_roll(sub), check_studies(sub)]
    if listdir is not None:
        checks.append(check_report(listdir))
    return checks


def local_reader(root):
    def read(path):
        p = os.path.join(root, path)
        if not os.path.isfile(p):
            return None
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read(MAX_FILE_BYTES + 1)

    def listdir(path):
        p = os.path.join(root, path)
        return os.listdir(p) if os.path.isdir(p) else []
    return read, listdir


def render(checks):
    """A Markdown report of the checks."""
    score, total = sum(c.score for c in checks), sum(c.points for c in checks)
    out = [f"**Format and consistency checks: {score} / {total}**", "",
           "| Check | Points | |", "|:--|--:|:-:|"]
    for c in checks:
        mark = "PASS" if c.passed else ("PARTIAL" if c.score else "FAIL")
        out.append(f"| {c.name} | {c.score} / {c.points} | {mark} |")
    notes = [c for c in checks if c.messages]
    if notes:
        out += ["", "**Details**", ""]
        for c in notes:
            out.append(f"*{c.name}*")
            out += [f"- {m}" for m in c.messages]
            out.append("")
    out += ["", "These checks look at the form of your results and at their internal consistency only. "
            "They do not tell you whether your numbers are correct: the accuracy of your MSI is checked separately."]
    return "\n".join(out)
