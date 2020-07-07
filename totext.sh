cd /home/anon/Documents/db/finra/pdf
for file in *.pdf
do
  pdftotext "$file" "$file.txt";
done
  # echo $(basename $file .shp)_poly.shp
