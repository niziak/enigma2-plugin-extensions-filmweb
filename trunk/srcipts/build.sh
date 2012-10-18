#!/bin/sh

PTH=usr/lib/enigma2/python/Plugins/Extensions/Filmweb
VER=1.1.2
ARC=mipsel
#ARC=unk
#ARC=sh4

opkg_extract_value() {
	sed -e "s/^[^:]*:[[:space:]]*//"
}

required_field() {
	field=$1

	value=`grep "^$field:" < ./tmp/CONTROL/control | opkg_extract_value`
	if [ -z "$value" ]; then
		echo "*** Error: ./tmp/CONTROL/control is missing field $field" >&2
		return 1
	fi
	echo $value
	return 0
}

cd ..
mkdir ./tmp
mkdir -p ./tmp/CONTROL
cp -R ./srcipts/control/* ./tmp/CONTROL

echo "Version: $VER" >> ./tmp/CONTROL/control
echo "Architecture: $ARC" >> ./tmp/CONTROL/control

pkg=`required_field Package`
version=`required_field Version | sed 's/Version://; s/^.://g;'`
arch=`required_field Architecture`

echo "Package: $pkg, Version: $version, Architecture: $arch"

rm -rf ${pkg}_${version}_${arch}.ipk

cd tmp
mkdir -p $PTH
cp -R ../src/* $PTH
rm -rf `find . -type d -name .svn`
rm -rf `find . -type f -name Filmweb.po`
tar zcvf data.tar.gz ./usr
cd CONTROL
tar zcvf ../../tmp/control.tar.gz ./*
cd ../../tmp
cp ../srcipts/debian-binary ./
ar -r ../${pkg}_${version}_${arch}.ipk ./debian-binary ./data.tar.gz ./control.tar.gz
cd ..
rm -rf tmp

