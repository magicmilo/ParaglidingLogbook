from .m0001_create_flights import upgrade as m0001_create_flights

MIGRATIONS = [
    (1, m0001_create_flights),
]
