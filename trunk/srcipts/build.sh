#!/bin/sh

opkg_extract_value() {
	sed -e "s/^[^:]*:[[:space:]]*//"
}

required_field() {
	field=$1

	value=`grep "^$field:" < ./control/control | opkg_extract_value`
	if [ -z "$value" ]; then
		echo "*** Error: ./control/control is missing field $field" >&2
		return 1
	fi
	echo $value
	return 0
}

pkg=`required_field Package`
version=`required_field Version | sed 's/Version://; s/^.://g;'`
arch=`required_field Architecture`

echo "Package: $pkg, Version: $version, Architecture: $arch"

cd ..
mkdir ./tmp
cd tmp
mkdir -p usr/lib/enigma2/python/Plugins/Extensions/Filmweb
cp -R ../src/* usr/lib/enigma2/python/Plugins/Extensions/Filmweb
rm -rf `find . -type d -name .svn`
rm -rf `find . -type f -name Filmweb.po`
tar zcvf data.tar.gz ./usr
cd ../srcipts/control
tar zcvf ../../tmp/control.tar.gz ./*
cd ../../tmp
cp ../srcipts/debian-binary ./
ar -r ../${pkg}_${version}_${arch}.ipk ./debian-binary ./data.tar.gz ./control.tar.gz
cd ..
rm -rf tmp

