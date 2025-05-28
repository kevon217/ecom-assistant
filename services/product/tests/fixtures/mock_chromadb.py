@pytest.fixture
def dummy_vector_store(tmp_path):
    return tmp_path / "chroma"
