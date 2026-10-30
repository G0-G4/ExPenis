#!/bin/sh
set -eu
apk add --no-cache e2fsprogs util-linux >/dev/null
image=/work/acceptance-640.ext4
mountdir=/mnt/expenis-acceptance
test ! -e "$image"
mkdir -p "$mountdir"
cleanup() {
  mountpoint -q "$mountdir" && umount "$mountdir" || true
  rm -f "$image"
}
trap cleanup EXIT
fallocate -l 400000000 "$image"
mkfs.ext4 -q -m 0 -F "$image"
mount -o loop,nosuid,nodev,noexec "$image" "$mountdir"
printf 'outside-data-preserved\n' >/work/canary
set +e
dd if=/dev/zero of="$mountdir/pressure" bs=1048576 count=450 oflag=direct 2>/work/dd-result
status=$?
set -e
test "$status" -ne 0
grep -q 'No space left on device' /work/dd-result
test "$(stat -c %s "$image")" = 400000000
test "$(cat /work/canary)" = outside-data-preserved
sync
umount "$mountdir"
e2fsck -fn "$image" >/work/fsck-result 2>&1
printf 'PASS: mounted 400000000-byte ext4 image enforced ENOSPC; clean fsck; outside canary preserved\n'
