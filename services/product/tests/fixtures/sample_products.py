@pytest.fixture
def sample_products_csv(tmp_path):
    csv_path = tmp_path / "test_products.csv"
    csv_content = """parent_asin,title_raw,__embed_text,features_raw,description_raw,categories_raw,details_raw,price,average_rating,rating_number,store,main_category,title_norm,features_norm
A1,Test Product 1,Test Product 1,"['feature1', 'feature2']","['desc1', 'desc2']","['cat1', 'cat2']","{""weight"": ""1 oz"", ""color"": ""black""}",10.0,4.5,100,TestStore,Electronics,test product 1,feature1 feature2
A2,Another Product,Another Product,"['feature3']","[]","['cat3']","{}",20.0,4.0,50,TestStore,Electronics,another product,feature3"""
    csv_path.write_text(csv_content)
    return csv_path
