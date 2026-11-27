# Q1b plan: role holders kept in plain getters

Fixed and committed **before** any Q1b data are fetched (tag `quantumclock-q1b-plan`).

## Why

Step 4 showed that the headline result depends on one unknown: whether Backed's role holders are one set of keys
for all its tokens or a separate set per token. The first collection (Q1) listed role holders only through
AccessControl (`getRoleMember`). Some tokens instead keep each holder in a plain public getter, such as `minter()`.
Q1b reads those getters.

## Rule

1. **Tokens:** every token in `data/q1_raw.json` whose ABI has at least one of the getters below
   (`qamp.extraction.q1b_targets`). On the Q1 data this is 20 tokens, all Backed. No other selection.
2. **Getters read** (fixed list, `qamp.extraction.ROLE_GETTERS`): `minter()`, `burner()`, `pauser()`,
   `multiplierUpdater()`, `blacklister()`, `masterMinter()`, `rescuer()`. Each is read only if the token's ABI has it.
3. **For each holder found:** the same controller facts as Q1 (contract or not, transaction count, Safe threshold and
   signers, timelock delay, owner), with one hop to signers.
4. **Events:** the matching role-change events on the token (`NewMinter`, `NewBurner`, `NewPauser`,
   `NewMultiplierUpdater`, `BlacklisterChanged`, `MasterMinterChanged`, `RescuerChanged`) and, for holders that are
   contracts, the same controller events as Q1.
5. **State:** latest block at the time of the run, recorded in the output (as in Q1).

## How the data are used (fixed now)

- Q1b records are added to the Q1 records when they are loaded (`qamp.extraction.merge_role_getters`). The Q1 file
  and its digest are not changed.
- A role holder read from a getter becomes an observed controller. As everywhere else, one anchor per key address.
  Tokens that share a holder therefore share an anchor.
- The **main run** uses the observed holders. Anchors that are still not observable keep one placeholder per token
  (the default). The `--unobserved-roles per_issuer` run stays as a sensitivity check for those.
- A getter that fails or returns the zero address adds nothing; the placeholder stays.
- No result from Q1b will be dropped or re-fetched to change an outcome. Errors are reported as they are.

## Outputs

| File | Content |
|---|---|
| `data/q1b_raw.json` | per token: getters, holder facts, events, errors; block, time, plan tag and commit |
| `data/q1b_summary.json` | counts and `sha256_raw` of the records |
| `notebooks/runs/` | executed notebook |

## How to run

Open `notebooks/Q1b_fetch_role_getters.ipynb` in Colab at tag `quantumclock-q1b-plan`, run all, and paste a **new**
free Etherscan key into the hidden prompt. About 600 calls, a few minutes. Delete the key afterwards.
