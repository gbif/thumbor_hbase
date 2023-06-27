# Notes for the GBIF deployment

Additional metadata is recorded in the HBase table, including image size and number of hits (to HBase)

    create 'thumbor',
      {NAME => 'image', IS_MOB => 'true', MOB_THRESHOLD => '524288', IS_MOB => 'true', 'BLOCKCACHE' => 'false', 'BLOCKSIZE' => '262144'},
      {NAME => 'metadata'},
      {NUMREGIONS => 128, SPLITALGO => 'HexStringSplit'}

    scan 'thumbor',
      {COLUMNS => ['metadata:image_size:toLong', 'metadata:created:toLong', 'metadata:accessed:toLong', 'metadata:hits:toLong', 'metadata']}

The table is also present in Hive:

```
CREATE EXTERNAL TABLE thumbor.thumbor7 (
  key string,
  created bigint,
  accessed bigint,
  dataset_key string,
  occurrence_id bigint,
  hostname string,
  identifier string,
  identifier_hash string,
  image_size bigint,
  hits bigint,
  unsafe string,
  retrieval_time_ms bigint,
  ts timestamp,
  image binary
)
STORED BY 'org.apache.hadoop.hive.hbase.HBaseStorageHandler'
WITH SERDEPROPERTIES (
  'hbase.columns.mapping'=':key,metadata:created,metadata:accessed,metadata:dataset_key,metadata:occurrence_id,metadata:hostname,metadata:identifier,metadata:identifier_hash,metadata:image_size,metadata:hits,metadata:unsafe,metadata:retrieval_time_ms,:timestamp,image:value',
  'hbase.table.default.storage.type'='binary',
  'serialization.format'='1')
TBLPROPERTIES ('hbase.table.name'='thumbor7');

SELECT key, created, accessed, dataset_key, occurrence_id, hostname, identifier, identifier_hash, image_size, hits, unsafe, ts FROM thumbor.thumbor7 LIMIT 10;

SELECT hostname, FLOOR(ROUND(AVG(image_size))) AS avg_size, COUNT(*) AS number_images, SUM(hits) AS total_hits, SUM((hits-1)*image_size) AS bandwidth_saved FROM thumbor.thumbor7 GROUP BY hostname ORDER BY avg_size;

SELECT COUNT(*) AS number_images, SUM(hits) AS total_hits, SUM((hits-1)*image_size) AS bandwidth_saved FROM thumbor.thumbor7;
```
