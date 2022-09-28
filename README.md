# Data download

Program to parse csv response and download vehicle images from WIM api using tanda/http protocol.
Tested using `Python 3.7.9`.

## How to run

1. Clone this repository
1. Download dependencies:

    ```powershell
    pip install -r requirements.txt
    ```

    - you will need to install Python

1. Check if version number is in the WIM api
   - If it does, use `-l=True` or `--link_has_number=True`
   - If it does **not**, use `-l=Flase` or `--link_has_number=False`

1. Verify remote `class/list`
   - It was found in testing, that different devices have diferent ucid numbers saved locally (There probably is a global class list somewhere)
   - Just go to the `class/list` API endpoint and check that it does not differ much from ucids in `datadwn/logic.py@resolve_ucid`
