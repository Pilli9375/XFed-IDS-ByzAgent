#!/bin/sh
# sheet.sh <dir> <out.png> <cols> <tilewidth> : tile every png in <dir> (sorted by frame) into one image
dir=$1; out=$2; cols=${3:-2}; w=${4:-960}
files=$(ls "$dir"/*.png | sort -t- -k2 -n)
n=$(echo "$files" | wc -l); rows=$(( (n + cols - 1) / cols ))
args=""; i=0
for f in $files; do args="$args -i $f"; i=$((i+1)); done
ffmpeg -hide_banner -loglevel error -y $args -filter_complex "$(i=0; for f in $files; do printf "[%d:v]scale=%d:-1,drawtext=text='%s':x=8:y=8:fontsize=22:fontcolor=red:box=1:boxcolor=white@0.8[v%d];" $i $w "$(basename $f .png | sed 's/element-//')" $i; i=$((i+1)); done; i=0; for f in $files; do printf "[v%d]" $i; i=$((i+1)); done; printf "xstack=inputs=%d:layout=" $n; i=0; for f in $files; do c=$((i % cols)); r=$((i / cols)); [ $i -gt 0 ] && printf "|"; xs=""; [ $c -eq 0 ] && xs=0; [ $c -gt 0 ] && xs=$(seq -s+ 1 $c | sed "s/[0-9]*/w0/g"); ys=""; [ $r -eq 0 ] && ys=0; [ $r -gt 0 ] && ys=$(seq -s+ 1 $r | sed "s/[0-9]*/h0/g"); printf "%s_%s" "$xs" "$ys"; i=$((i+1)); done; printf ":fill=black")" "$out"
