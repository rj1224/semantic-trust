select cast('2024-01-01' as date) + cast(i as integer) as date_day from range(0, 100) as t(i)
