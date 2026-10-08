# Goals League website

A static site showing your 12-team, goals-only fantasy league: table, fixtures/results
and top scorers. It updates itself automatically — a scheduled job pulls goal data from
the official Fantasy Premier League API every 15 minutes and commits the new scores,
which GitHub Pages then redeploys.

## One-time setup (about 10 minutes)

1. **Create a new GitHub repository.**
   Go to [github.com/new](https://github.com/new), name it anything (e.g. `goals-league`),
   set it to **Public** (so the scheduled updates run for free with no minute limits),
   and click *Create repository*. Don't initialise it with a README.

2. **Upload these files.**
   On the new repo's page, click *uploading an existing file* and drag in everything from
   this folder — keeping the folder structure (`data/`, `scripts/`, `.github/workflows/`,
   plus `index.html`, `style.css`, `app.js`, `.nojekyll`). If the upload box won't take
   folders, use the "Add file → Upload files" button and drag the whole unzipped folder in,
   or use these commands instead from inside the unzipped folder:
   ```
   git init
   git add .
   git commit -m "Initial site"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

3. **Turn on GitHub Pages.**
   In the repo, go to *Settings → Pages*. Under "Build and deployment", set
   **Source: Deploy from a branch**, branch **main**, folder **/ (root)**, then *Save*.
   After a minute or two your site will be live at:
   `https://<your-username>.github.io/<your-repo>/`

4. **Turn on the scheduled updates.**
   Go to the *Actions* tab and click "I understand my workflows, go ahead and enable them"
   if prompted. That's it — the `Update league scores` workflow will now run automatically
   every 15 minutes, and you can also trigger it manually any time from the Actions tab
   ("Update league scores" → *Run workflow*).

## How it works

- `data/rosters.json` — the 12 squads (player, club, position, price paid), each player
  tagged with their official FPL ID so the lookup is never thrown off by name spelling.
- `data/fixtures.json` — the pairing for every one of the 38 gameweeks.
- `data/results.json` — gameweeks 1–5 are locked in from your manual results and are never
  touched by the automation. From gameweek 6 onward, `scripts/update_scores.py` fills this
  in once each gameweek kicks off, using FPL's live per-gameweek stats: a goal by one of
  your players counts for your team, an own goal by one of your players counts for your
  *opponent* (per your league's rule), and the status moves scheduled → live → final.
- `data/standings.json` — the league table, recomputed from `results.json` on every run
  (3 points for a win, 1 for a draw, ties broken by goal difference then goals scored).

## Changing a roster mid-season

If a trade or replacement happens, edit the relevant entry in `data/rosters.json` (you'll
need the new player's FPL element ID — ask me and I'll look it up) and commit the change;
the next scheduled run will pick it up automatically.
