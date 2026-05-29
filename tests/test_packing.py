import commitword as sw


def test_pack1_bijection_full_domain():
    for y in range(sw.Y_MIN, sw.Y_MIN + 40):          # incl. y > 29 (uncapped)
        for k in range(sw.K_MIN, sw.K_MAX + 1):
            n = sw.pack1(y, k)
            assert sw.unpack1(n) == (y, k)


def test_pack2_bijection():
    for m in range(sw.M_MIN, sw.M_MAX + 1):
        assert sw.unpack2(sw.pack2(m)) == m


def test_pack1_known_values():
    # threats49thirty: N1=49 -> y=15, k=14
    assert sw.unpack1(49) == (15, 14)
    assert sw.pack1(10, 10) == 0


def test_defaults():
    assert sw.HASH_NAME == "sha1"
    assert sw.WORDLIST_PATH.name == "curated.txt"
