# OE3035 Project: Motion Sickness Incidence on Board

This is your group's repository for the project of OE3035. The task is described in the
[project chapter of the course notes](https://oe3035.mavlab.in/project/project.html). Read it first.
This README explains only **what to put where**, and **how your work is checked**.

## What goes where

| Folder | What you put there |
|:--|:--|
| `src/` | All the code that produces your numbers and plots, in any language (Python, MATLAB, ...). |
| `results/` | Your numbers, in the four CSV files described below. **Their format is checked automatically.** |
| `report/` | Your report, as a PDF (for example `report/report.pdf`). |
| `data/` | The HydRA results of your hulls. Not committed (it is in `.gitignore`). |
| `tools/` | Helper scripts from the course staff. Do not edit them. |

To download the HydRA results of your variant and its baseline into `data/`:

```sh
python tools/get_data.py KCS_L1p100        # use the name of your own variant
```

## The result files

Fill in the four files in `results/`. Each already holds its header line; add one row per line
below it, in SI units, with **at least four significant figures**. Lines starting with `#` are
ignored. The hull names are the member names of the HydRA results, such as `KCS_L1p000` (the
baseline) and `KCS_L1p100` (a variant). Write the files from your code rather than by hand,
for example with `csv.writer`, `pandas.DataFrame.to_csv` or MATLAB's `writetable`.

### `results/msi_cases.csv`: the 30 cases (Deliverable 3)

One row for each of your two hulls, each heading and each speed: 30 rows.

| Column | Meaning | Unit |
|:--|:--|:--|
| `hull` | member name, e.g. `KCS_L1p100` | |
| `beta_deg` | wave heading β: `90`, `135` or `180` | deg |
| `fn_ratio` | Fn/Fn_des: `0.90`, `0.95`, `1.00`, `1.05` or `1.10` | |
| `U_mps` | ship speed U, as in the HydRA results file | m/s |
| `sigma_a` | standard deviation σₐ of the vertical acceleration of the cabin | m/s² |
| `abar` | mean absolute acceleration ā | m/s² |
| `we_bar` | mean frequency ω̄ₑ of the acceleration spectrum | rad/s |
| `mu_msi` | μ_MSI of the O'Hanlon and McCauley model | |
| `msi_pct` | motion sickness incidence in 2 h | % |

```csv
hull,beta_deg,fn_ratio,U_mps,sigma_a,abar,we_bar,mu_msi,msi_pct
KCS_L1p000,90,0.90,11.1132,0.4955,0.3954,0.8366,-0.8051,7.029
```

(Apart from the speed, the numbers of this example are made up: they show the format, not a result.)

### `results/roll_damping.csv`: the roll damping (Deliverable 2)

One row per hull.

| Column | Meaning | Unit |
|:--|:--|:--|
| `hull` | member name | |
| `omega_n` | roll natural frequency ωₙ | rad/s |
| `zeta_wave` | wave-making roll damping at ωₙ, as a fraction of critical | |
| `Bv44` | the viscous roll damping B_v,44 you added (ζ_v = 0.05) | N m s |

### `results/sensitivity.csv`: the parameter studies (Deliverables 5d and 5e)

At least one row for each of the five studies below. Pick one of your hulls and one speed for
each; other columns as in `msi_cases.csv`.

| `study` | `beta_deg` | `x_P_m` | `y_P_m` | `zeta_v` |
|:--|--:|:--|:--|:--|
| `cabin_midship` | 180 | 0 | +0.4B | 0.05 |
| `cabin_centreline` | 90 | the project x_P | 0 | 0.05 |
| `cabin_starboard` | 90 | the project x_P | −0.4B | 0.05 |
| `damping_low` | 90 | the project x_P | +0.4B | 0.025 |
| `damping_high` | 90 | the project x_P | +0.4B | 0.10 |

`x_P_m` and `y_P_m` are the cabin position you used, in metres, as numbers: for the KCS, for
example, `cabin_centreline` has `x_P_m = -80.5` and `y_P_m = 0`.

### `results/spikes.csv`: the points you replaced (Deliverable 2)

One row per computed point you replaced as an irregular-frequency spike: `hull`, `beta_deg`,
`fn_ratio`, and the **wave** frequency `omega` (rad/s) of the point. Leave only the header if
you replaced none. This file is not scored, but the staff read it.

## How your work is checked

Two checks run on your results. Neither of them ever shows you a correct answer.

1. **Format and consistency, on every push.** The Classroom 50 autograder checks that the
   result files are complete and well formed, that your speeds are those of the HydRA
   results, and that ā, μ_MSI and the MSI follow from your σₐ and ω̄ₑ by the formulas of the
   chapter. It does not look at whether your σₐ and ω̄ₑ are right. Its score (out of 20)
   appears as a Release of your repository and as a check mark on your commit. Run the same
   checks before you push:

   ```sh
   python tools/check_submission.py
   ```

2. **Accuracy, a few times a day.** The course staff compare your numbers with their own
   solution, and report back in an issue of your repository titled *Autograder: accuracy of
   your MSI results*. For each case it says whether σₐ, ω̄ₑ and the MSI are within tolerance
   (✅), close (🟡) or off (❌), never what the right value is. Only commits that change the
   files in `results/` are checked again, and a commit status `oe3035/msi-accuracy` shows the
   score of your latest commit.

   The tolerances allow for every reasonable choice of method: the interpolation scheme, the
   frequency step, the taper, the way you replace spikes. A ❌ therefore means that a step of
   your calculation needs another look, not that a decimal is off. The chapter's
   *Before you trust your RAOs* box and the check values of its tables are the best place
   to start looking.

The numbers are only part of the grade: the report, its derivation and its discussion are
graded by the staff.

## Working as a group

- Commit early and often, with clear messages; everyone in the group should commit.
- Pull before you start working (`git pull`), to avoid conflicts.
- Do not rewrite history (no `git push --force`): it is blocked, and the history is part of
  your submission.
- Keep `src/` able to reproduce every number in `results/` and every figure in the report.
