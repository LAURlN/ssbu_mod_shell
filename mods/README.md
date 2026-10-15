# Mod repositories

Each folder here is its own git repository and is ignored by the workspace repo.

- `ssbu_mod_new/` - the user's mod, from https://github.com/LAURlN/ssbu_mod_new.
  On 2026-10-01 that remote had no commits, so nothing could be cloned. Once it is pushed:
  `git clone https://github.com/LAURlN/ssbu_mod_new.git mods/ssbu_mod_new`, then add an inbox task
  to fold its notes into `kb/` and its tools into `tools/`.

Agents work on a branch named `lab/<task id>` inside a mod repo and never push.
