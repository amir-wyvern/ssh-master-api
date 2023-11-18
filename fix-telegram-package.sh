sed 's/from collections import namedtuple, Mapping/from collections import namedtuple\nfrom collections.abc import Mapping/' venv/lib/python3.10/site-packages/telegram/vendor/ptb_urllib3/urllib3/util/selectors.py > venv/lib/python3.10/site-packages/telegram/vendor/ptb_urllib3/urllib3/util/selectors2.py
mv venv/lib/python3.10/site-packages/telegram/vendor/ptb_urllib3/urllib3/util/selectors2.py venv/lib/python3.10/site-packages/telegram/vendor/ptb_urllib3/urllib3/util/selectors.py

sed 's/from collections import Mapping, MutableMapping/from collections.abc import Mapping, MutableMapping/' venv/lib/python3.10/site-packages/telegram/vendor/ptb_urllib3/urllib3/_collections.py > venv/lib/python3.10/site-packages/telegram/vendor/ptb_urllib3/urllib3/_collections2.py
mv venv/lib/python3.10/site-packages/telegram/vendor/ptb_urllib3/urllib3/_collections2.py venv/lib/python3.10/site-packages/telegram/vendor/ptb_urllib3/urllib3/_collections.py
