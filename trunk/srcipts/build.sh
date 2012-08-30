#!/bin/sh

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
ar -r ../enigma2-plugin-extensions-filmweb_1.0.2_all.ipk ./debian-binary ./data.tar.gz ./control.tar.gz
cd ..
rm -rf tmp
