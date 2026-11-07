# Guide: official runs without a local environment (GitHub web interface + GitHub Actions)

You need only a browser and the ability to unzip a file. Every click path is for github.com.

## Part A. Put the files on GitHub (about 15 minutes)

1. Unzip `rwa-threatlab-upload.zip` on your computer (double-click). You get a folder `rwa-threatlab` and a file `official-run.yml`.
2. Open your repository, **Add file -> Upload files**. Drag the whole `rwa-threatlab` folder onto the page (folder structure is kept; GitHub accepts up to 100 files per upload, so if there are two zips, upload one, commit, then the other). Commit directly to `main` with the message "Journal extension: freeze, pre-registration, real-trace tooling".
3. **Add file -> Create new file**. In the name box type `.github/workflows/rwa-threatlab-official-run.yml` (typing `/` creates the folders). Paste the full contents of `official-run.yml`. Commit to `main`.
4. Open the **Actions** tab. The existing workflow "rwa-threatlab CI" starts by itself. **Wait until it is green** (tests on Python 3.10, 3.11 and 3.12). If it is red, read the error, fix it and push, and only go on when it is green.

## Part B. Pre-register (this is the timestamp)

5. Recommended independent timestamp: on https://osf.io create a project, choose **Registrations -> New registration -> Open-Ended Registration**, upload `docs/PREREGISTRATION.md` and `docs/FREEZE.json`, and register. OSF registrations cannot be edited afterwards. (Zenodo's GitHub integration also gives a DOI, but it archives the whole repository, including the `ResearchPapers` folder of other authors' PDFs and your interview notes, so prefer a clean separate repository for that.)
6. On your repo: **Releases -> Draft a new release**. In "Choose a tag" type `v1.3-prereg-real` and pick "Create new tag on publish". Target `main`. Title "Pre-registration, real-trace experiments". Description "Frozen instrument and pre-registration. No real data has been run." **Publish release.**

From here on do not change any file under `rwa-threatlab/src`, `tests` or `scripts`. If a change is unavoidable, record it as a logged deviation (`docs/PREREGISTRATION.md` section 6) and re-freeze.

## Part C. Official run (OFAC, stage 1)

7. **Actions -> rwa-threatlab official run -> Run workflow**. Keep `ref = v1.3-prereg-real` and `sections = ofac`. Click Run. It takes about 5-10 minutes.
8. Open the run. Every step must be green. The last step prints the results branch, `official-run-<number>`. Results are also attached to the run as an artifact (retained 90 days by default).
   * If "Fetch OFAC change files" fails (treasury.gov may refuse automated downloads), download the five files in your browser from the links in `docs/data/datasets.json`, upload them to `rwa-threatlab/docs/data/raw/` on `main` (Add file -> Upload files), publish a new release `v1.3-prereg-real-data` (only data files were added), and run the workflow with that ref.
   * If the parse step stops with "unrecognised OFAC header", keep the log: the parser may need a fix, which must be committed and re-tagged before a new run.
9. Record the branch name and the run URL. For the independent re-run, clone that branch in a separate environment, run the identical command (`python -m rwa_threatlab real --only ofac --out <dir>`), compare the two `real.json` files with `scripts/compare_runs.py`, and then interpret the outcomes.

## Part D. After the run

10. On GitHub, open **Pull requests -> New pull request**, base `main`, compare `official-run-<number>`, review the changes (results, raw files, evidence folder) and merge. Publish a release `v1.3-real-results`.
11. Stage 2 (H14 timing, H15 bridge): export the two CSV files from public explorers as described in `docs/REAL_DATA_RUNBOOK.md`, upload them to `rwa-threatlab/docs/data/`, edit `docs/data/datasets.json` in the browser (pencil icon) to replace every `TODO` and to set the `*_column` fields to your CSV's exact header names, commit, publish release `v1.3-prereg-real2`, and run the workflow with that ref and `sections = timing bridge`.

## What this does and does not give you

* **Gives you:** a run on a clean machine from a fixed tag, the source files downloaded directly from the publisher and hashed, the run log that you cannot edit, every output on a branch with the evidence, and a re-run in a separate environment that must match exactly.
* **Does not give you:** an independent human replication. The replication is run within the research effort, in a separate environment. The strongest additional step is for someone else to click "Run workflow" on the same tag.
* **A tag can be moved by the repository owner.** The OSF registration (or a release archive) is what makes the pre-registration tamper-evident.
* **The compliance layer is simulated.** Real data drive sanctions events (order, not real time gaps), timing and latency only.
