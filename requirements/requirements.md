## bug fix
1. 修正 @dashboard.py中，課程卡片下的button的連結，改至課程卡片本身，點選卡片本身即可進入到 @session_detail.py中
2. @session_detail.py中按下報名會直接累加到額滿，但只需要加1個數量才對

## requirement
1. 報名時要填入姓名、若是已報名者中姓名已有重覆，則pop訊息您已報名，不讓報名。 若是姓名沒重覆，則可報名名額-1。課程報名同時也記錄在 project中的json檔，該json list包含著多個session json object, 同時把報名者的資訊記錄下來。
2. @session_detail.py 要可以顯示已報名的人有誰。
3. @dashboard.py右上角的管理者權限，點選輸入帳號/密碼後，可以進行「新增課程資訊」「編輯課程資訊」