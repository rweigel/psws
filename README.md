Assumes magnetometer data in directories as under `data/` - each subdir corresponds to data from a station with ID in `catalog.csv`.

Return response to `/hapi/catalog` request

```
python catalog.py
```

Return response to `/hapi/info` request

```
python info.py S000028
```

Return response to `/hapi/data` request

```
python data.py W2NAF 2025-10-20 2025-10-21
```