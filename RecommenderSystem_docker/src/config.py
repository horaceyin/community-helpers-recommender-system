from collections import OrderedDict

DISTRICT = ['Islands', 'Kwai Tsing', 'North', 'Sai Kung', 'Sha Tin', 'Tai Po', 
            'Tsuen Wan', 'Tuen Mun', 'Yuen Long', 'Kowloon City', 'Kwun Tong', 
            'Sham Shui Po', 'Wong Tai Sin', 'Yau Tsim Mong', 
            'Central and Western', 'Eastern', 'Southern', 'Wan Chai']

model_spec = {
    'inputs': {
        'userId': {'default': '', 'type': 'str'},
        'helpRequestId': {'default': '', 'type': 'str'},
        'age': {'default': -1, 'type': 'int'},
        'userDistrict': {'default': '', 'type': 'str'},
        'gender': {'default': '', 'type': 'str'},
        'userInterest': {'default': '', 'type': 'str'},
        'category': {'default': '', 'type': 'str'},
        'title': {'default': '', 'type': 'str'},
        'description': {'default': '', 'type': 'str'},
        'helpRequestDistrict': {'default': '', 'type': 'str'},
        'price': {'default': -1, 'type': 'float'}
    },
    'outputs': {
        'actionRate': {'default': -1, 'type': 'float'},
    },
    'feature_columns': {
        # Continuous Features, only go into deep
        'num': [
            {'feature': 'age'},
            {'feature': 'price'},
        ],
        # Categorical Features，onehot into wide，embedding into deep
        'cate': [
            {'feature': 'userDistrict', 'vocab': DISTRICT, 'embedding': 200},
            {'feature': 'gender', 'vocab': ['Male', 'Female'], 'embedding': 200},
            {'feature': 'helpRequestDistrict', 'vocab': DISTRICT, 'embedding': 200},
        ],
        'hash': [
            {'feature': 'title', 'bucket': 300, 'embedding': 300},
            {'feature': 'userInterest', 'bucket': 200, 'embedding': 200},
            {'feature': 'category', 'bucket': 200, 'embedding': 200},
            {'feature': 'description', 'bucket': 400, 'embedding': 240},
        ],
        'bucket': [
            {'feature': 'age', 'boundaries': [10, 20, 30, 40, 50, 60, 70, 80, 90], 'embedding': 200}
        ],
        # Cross Product Transformation, go into wide
        'cross': [
            # {'feature': ['age#bucket', 'category#hash'], 'bucket': 20},
            {'feature': ['userDistrict#cate', 'helpRequestDistrict#cate'], 'bucket': 200},
            # {'feature': ['gender#cate', 'helpRequestDistrict#cate'], 'bucket': 20},
        ]
    }
}