#!/bin/bash
# Build the CMTV Nuvio TV app (2026-09-29). Usage: build.sh <nuvio tag, e.g. 1.0.0> <cmtv rev, e.g. 1>
# Clean checkout of the tag -> apply_cmtv.py -> commit on branch cmtv-<tag> -> signed release APKs in /opt/nuvio-build/out/.
# Signing key: /opt/nuvio-server-cmtv/app-signing/ (in the nightly encrypted backup). NEVER lose it: customers can only
# update over an app signed with the same key.
set -euo pipefail
TAG=${1:?nuvio tag}; REV=${2:-1}
B=/opt/nuvio-build; SRC=$B/NuvioTV; C=/opt/nuvio-server-cmtv; K=$C/app-signing
export ANDROID_HOME=/opt/android-sdk ANDROID_SDK_ROOT=/opt/android-sdk
cd $SRC
git fetch -q --tags origin
git checkout -q -f "refs/tags/$TAG"
git clean -q -fdx -e local.properties
git checkout -q -B "cmtv-$TAG"

# signing key (made once)
if [ ! -f $K/cmtv-nuvio.jks ]; then
  install -d -m 700 $K
  openssl rand -base64 24 | tr -d '/+=' > $K/password; chmod 600 $K/password
  keytool -genkeypair -v -keystore $K/cmtv-nuvio.jks -alias cmtv -keyalg RSA -keysize 4096 -validity 36500 \
    -storepass "$(cat $K/password)" -keypass "$(cat $K/password)" -dname "CN=CMTV, O=CMTV, C=CA" > /dev/null 2>&1
  chmod 600 $K/cmtv-nuvio.jks; echo "made the signing key"
fi

# settings (public values only; local.properties is not committed)
ANON=$(grep -E '^ANON_KEY=' /opt/nuvio-server/.env | cut -d= -f2-)
{ echo "sdk.dir=$ANDROID_HOME"
  echo "NUVIO_SUPABASE_URL=https://nuvio.cmtv.info"
  echo "NUVIO_SUPABASE_ANON_KEY=$ANON"
  echo "TV_LOGIN_WEB_BASE_URL=https://nuvio.cmtv.info/tv-login"
  echo "DEVICE_LOGIN_WEB_BASE_URL=https://nuvio.cmtv.info/link"
  echo "AVATAR_PUBLIC_BASE_URL=https://nuvio.cmtv.info/storage/v1/object/public/avatars"
  [ -s $C/app-tmdb-key ] && echo "TMDB_API_KEY=$(cat $C/app-tmdb-key)"
} > local.properties

/opt/backend/venv/bin/python /opt/nuvio-server-cmtv/app/apply_cmtv.py "$REV" /opt/frontend/public/cmtv/favicon-192.png
cp /opt/nuvio-server-cmtv/app/README-CMTV.md . 2>/dev/null || true
mkdir -p cmtv && cp /opt/nuvio-server-cmtv/app/apply_cmtv.py /opt/nuvio-server-cmtv/app/build.sh cmtv/   # published with the source
git add -A
git -c user.name="CMTV" -c user.email="cmtv@pm.me" commit -q -m "CMTV build of Nuvio TV $TAG (rev $REV): our server built in, username sign-in, updates from CMTV billing, CMTV badge, app id info.cmtv.nuvio" || true

export NUVIO_RELEASE_STORE_FILE=$K/cmtv-nuvio.jks NUVIO_RELEASE_KEY_ALIAS=cmtv
export NUVIO_RELEASE_STORE_PASSWORD="$(cat $K/password)" NUVIO_RELEASE_KEY_PASSWORD="$(cat $K/password)"
./gradlew --no-daemon -q :app:assembleFullRelease > $B/gradle-$TAG-$REV.log 2>&1 || { tail -40 $B/gradle-$TAG-$REV.log; exit 1; }
mkdir -p $B/out
for f in app/build/outputs/apk/full/release/*.apk; do
  n=$(basename "$f" | sed -E "s/^app-full-/Nuvio-CMTV-$TAG-cmtv.$REV-/; s/-release//")
  cp "$f" "$B/out/$n"
done
ls -la $B/out | grep "$TAG-cmtv.$REV"
