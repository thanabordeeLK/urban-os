# ตัวอย่างคำสั่ง ogr2ogr สำหรับนำข้อมูลเข้า PostGIS

## Shapefile ถนน
ogr2ogr -f "PostgreSQL" PG:"host=<HOST> dbname=<DB> user=<USER> password=<PASSWORD>" roads.shp -nln urban_os.roads -nlt PROMOTE_TO_MULTI -lco GEOMETRY_NAME=geom -t_srs EPSG:4326 -append

## GeoPackage บริการสาธารณะ
ogr2ogr -f "PostgreSQL" PG:"host=<HOST> dbname=<DB> user=<USER> password=<PASSWORD>" public_facilities.gpkg public_facilities -nln urban_os.public_facilities -nlt PROMOTE_TO_MULTI -lco GEOMETRY_NAME=geom -t_srs EPSG:4326 -append

## GeoJSON zoning
ogr2ogr -f "PostgreSQL" PG:"host=<HOST> dbname=<DB> user=<USER> password=<PASSWORD>" zoning.geojson -nln urban_os.zoning -nlt PROMOTE_TO_MULTI -lco GEOMETRY_NAME=geom -t_srs EPSG:4326 -append