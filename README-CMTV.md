# Nuvio TV: CMTV build

This branch is [Nuvio TV](https://github.com/NuvioMedia/NuvioTV) by NuvioMedia, licensed under the GNU GPL v3,
with a small set of changes by CMTV so it works with CMTV's own Nuvio server:

- The built-in server is `https://nuvio.cmtv.info`; sign-in is username + password on the TV
  (a username without "@" is sent as `<username>@nuvio.cmtv.info`).
- Separate app id `info.cmtv.nuvio` (installs next to the official Nuvio); version `<upstream>-cmtv.<n>`.
- In-app updates come from CMTV (`billing.cmtv.info`) instead of Nuvio's GitHub releases; server switching is off.
- Sign-in texts mention CMTV; a small CMTV badge is added to the icon and TV banner.

All changes are made by `apply_cmtv.py` in the commit on top of the upstream release tag. Everything else is Nuvio's
work: see the upstream project for its licence, credits and source. This build is not an official Nuvio release.
