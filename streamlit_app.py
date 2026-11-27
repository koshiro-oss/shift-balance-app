import streamlit as st
import json
from datetime import datetime, date
import calendar as py_calendar
from streamlit_calendar import calendar as st_calendar
import uuid
import os
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL,SUPABASE_KEY)

st.title("収支管理アプリ")

###=====================
####   Supabase
###=====================
###=====================
####     Shift CRUD
###=====================
def save_shift(shift):

    (supabase.table("shifts").insert(shift).execute())
def load_shifts():

    result = (supabase.table("shifts").select("*").execute())

    return result.data
def delete_shift(record_id):

    (supabase.table("shifts").delete().eq("id", record_id).execute())
def update_shift(shift):
    (supabase.table("shifts").update({
            "workplace": shift["workplace"],
            "work_date": shift["work_date"],
            "pay_date": shift["pay_date"],
            "start_time": shift["start_time"],
            "end_time": shift["end_time"],
            "break_minutes": shift["break_minutes"],
            "hourly_wage": shift["hourly_wage"],
            "salary": shift["salary"]
        }).eq("id", shift["id"]).execute())

###======================
####    Expensee CRUD
###======================
def save_expense(expense):

    (supabase.table("expenses").insert(expense).execute())
def load_expenses():

    result = (supabase.table("expenses").select("*").execute())

    return result.data
def delete_expense(record_id):

    (supabase.table("expenses").delete().eq("id", record_id).execute())
def update_expense(expense):
    (supabase.table("expenses").update({
            "purpose": expense["purpose"],
            "memo": expense.get("memo", ""),
            "due_date": expense["due_date"],
            "amount": expense["amount"]
        }).eq("id", expense["id"]).execute())

###======================
####    Balance CRUD
###======================
def save_balance(current_balance):

    (supabase.table("app_settings").update({"current_balance": current_balance}).eq("id", 1).execute())

def load_balance():

    result = (supabase.table("app_settings").select("current_balance").eq("id", 1).execute())
    return result.data[0]["current_balance"]

###===================
####     Master
###===================
def save_master(workplaces, expense_colors):

    master = {"workplaces": workplaces,"expense_colors": expense_colors}
    with open("master.json", "w", encoding="utf-8") as file:
        json.dump(master,file,ensure_ascii=False,indent=4)


def load_master():

    with open("master.json","r",encoding="utf-8") as file:
        master = json.load(file)

    return master

master = load_master()
WORKPLACES = master["workplaces"]
EXPENSES_COLORS = master["expense_colors"]

###===================
####     Utility
###===================
def float_to_time(value):
    hour = int(value)
    minute = round((value - hour) * 60)
    return datetime.strptime(f"{hour:02d}:{minute:02d}","%H:%M").time()

def calculate_pay_date(work_date, workplace):
        #work_date = datetime.strptime(work_date,"%Y-%m-%d")#文字列のwor_dateをカレンダ上の日付データに変更
        #%Y: 年、%m: 月、%d: 日付
        year = work_date.year
        month = work_date.month
        day = work_date.day#年、月、日付を数値データとして取り出し
        if workplace == "ミスド":
            if day <= 20:
                month += 1 #monthに1たす
            else:
                month += 2 #monthに2たす
            if month > 12: #monthが13とか14になったら
                month -= 12 #12引く
                year += 1 #年に1たす
            return f"{year}-{month:02d}-05"
        
        elif workplace == "コールセンター":
            month += 1
            if month > 12:
                month -= 12 #12引く
                year += 1 #年に1たす
            last_day = py_calendar.monthrange(year, month)[1]
            return f"{year}-{month:02d}-{last_day}"

###==================
####   Calculation
###==================

# 共通データ
shifts = load_shifts()
expenses = load_expenses()
current_balance = load_balance()

months = []
months = sorted(list(set([shift["pay_date"][:7] for shift in shifts] + [expense["due_date"][:7] for expense in expenses])))

if not months:
    months = [date.today().strftime("%Y-%m")]
year = date.today().year
month = date.today().month
for i in range(12):
    current_month = month + i
    current_year = year
    while current_month > 12:
        current_month -= 12
        current_year += 1
    months.append(f"{current_year}-{current_month:02d}")
target_month = st.selectbox("対象月",months)
    
#当月の月収の計算
def calculate_monthly_income(shifts, target_month):
    monthly_income = 0  # 全体の総支給額
    # 勤務地ごとの金額を保存する箱を、WORKPLACESから自動で作る
    workplace_incomes = {workplace: 0 for workplace in WORKPLACES.keys()}
    #↓こう書いてる
    #workplace_incomes = {}
    #for workplace in WORKPLACES.keys():
    #workplace_incomes[workplace] = 0
    for shift in shifts:
        # 指定された支払月（pay_dateの「YYYY-MM」部分）が一致するかチェック
        if target_month == shift["pay_date"][0:7]:
            salary = shift["salary"]
            wp = shift["workplace"]
            
            monthly_income += salary
            
            # 勤務地ごとの合計にも足す（WORKPLACESに含まれている勤務地なら）
            if wp in workplace_incomes:
                workplace_incomes[wp] += salary
            else:
                monthly_income = monthly_income
    return monthly_income, workplace_incomes

#当月の支出
def calculate_monthly_expense(expenses,target_month):
    monthly_expense = 0
    for expense in expenses:
        if target_month == expense["due_date"][0:7]:
            monthly_expense = monthly_expense + expense["amount"]
        else:
            monthly_expense = monthly_expense

    #st.metric("支出予定", f"{monthly_expense}円")
    return monthly_expense

#当月の不足額
def calculate_balance(monthly_income, monthly_expense, target_month):
    balance = monthly_income - monthly_expense
    return balance

monthly_income = calculate_monthly_income(shifts,target_month)[0]
workplace_incomes = calculate_monthly_income(shifts,target_month)[1]
monthly_expense = calculate_monthly_expense(expenses,target_month)
balance = calculate_balance(monthly_income, monthly_expense, target_month)

future_balance = current_balance + balance
balance_color = ( "#dcfce7"
                 if future_balance >= 0
                 else "#fee2e2")

### カレンダー ###
calendar_events = []

# シフト・給与イベント

for shift in shifts:
    color = WORKPLACES[shift["workplace"]]["color"]
    shift_id = shift["id"]

    # シフトイベント
    calendar_events.append({"id": f"shift_{shift_id}","title": shift["workplace"],"start": shift["work_date"],"color": color})

    # 給与イベント
pay_events = {}
for shift in shifts:
    key = (shift["workplace"],shift["pay_date"])
    if key not in pay_events:
        pay_events[key] = 0
    pay_events[key] += shift["salary"]
for (workplace, pay_date), total_salary in pay_events.items():
    calendar_events.append({"id": f"salary_{workplace}_{pay_date}",
                            "title": f"{workplace}給与 {total_salary}円",
                            "start": pay_date,
                            "color": "gold"})
# 支出イベント
for expense in expenses:
    color = EXPENSES_COLORS[expense["purpose"]]

    expense_id = expense["id"]

    calendar_events.append({"id": f"expense_{expense_id}","title": expense["purpose"],"start": expense["due_date"],"color": color})

calendar_events.sort(key=lambda calendar_event: calendar_event["start"])

 # -------------------
 # 削除処理
 # -------------------
# データ削除用の関数
def delete_data(event_type, record_id):

    if event_type == "shift":
        delete_shift(record_id)

    elif event_type == "expense":
        delete_expense(record_id)

# イベント詳細表示用のポップアップ
@st.dialog("イベント詳細")
def show_event_detail(event_type, record):

    record_id = record["id"]
    edit_key = f"editing_{event_type}_{record_id}"

    # 編集ボタン
    if st.button("編集", key=f"edit_button_{event_type}_{record_id}"):
        st.session_state[edit_key] = True

    # 編集モード
    if st.session_state.get(edit_key, False):
        st.subheader("編集フォーム")

        # -------------------
        # シフト編集
        # -------------------
        if event_type == "shift":

            with st.form("shift_edit_form"):

                workplace = st.selectbox("勤務先",list(WORKPLACES.keys()),index=list(WORKPLACES.keys()).index(record["workplace"]))
                work_date = st.date_input("勤務日",value=datetime.strptime(record["work_date"], "%Y-%m-%d").date())
                start_time = st.time_input("開始時間",value=float_to_time(record["start_time"]))
                end_time = st.time_input("終了時間",value=float_to_time(record["end_time"]))
                break_minutes = st.selectbox("休憩時間",[0, 15, 30, 45],index=[0, 15, 30, 45].index(record["break_minutes"]))
                submitted = st.form_submit_button("変更を保存")

                if submitted:

                    start_hour = start_time.hour + start_time.minute / 60
                    end_hour = end_time.hour + end_time.minute / 60
                    work_hours = end_hour - start_hour - break_minutes / 60

                    if work_hours <= 0:

                        st.error("勤務時間が不正です")

                    else:
                        hourly_wage = WORKPLACES[workplace]["hourly_wage"]
                        salary = int(work_hours * hourly_wage)
                        pay_date = calculate_pay_date(work_date, workplace)

                        # 元データを書き換える
                        record.update({"workplace": workplace,"work_date": str(work_date),"start_time": start_hour,"end_time": end_hour,"break_minutes": break_minutes,
                                       "hourly_wage": hourly_wage,"salary": salary,"pay_date": str(pay_date)})

                        update_shift(record)

                        st.session_state[edit_key] = False
                        st.success("変更を保存しました！")
                        st.rerun()
        # -------------------
        # 支出編集
        # -------------------
        elif event_type == "expense":

            with st.form("expense_edit_form"):

                purpose = st.selectbox("項目",list(EXPENSES_COLORS.keys()),index=list(EXPENSES_COLORS.keys()).index(record["purpose"]))
                memo = st.text_input("メモ",value=record.get("memo", ""))
                due_date = st.date_input("使用日",value=datetime.strptime(record["due_date"], "%Y-%m-%d").date())
                amount = st.number_input("料金",min_value=0,value=int(record["amount"]),step=100)
                submitted = st.form_submit_button("変更を保存")

                if submitted:

                    record.update({"purpose": purpose,"memo": memo,"due_date": str(due_date),"amount": int(amount)})

                    update_expense(record)

                    st.session_state[edit_key] = False
                    st.success("変更を保存しました！")
                    st.rerun()

    # -------------------
    # 詳細表示モード
    # -------------------
    else:

        if event_type == "shift":

            st.subheader("シフト詳細")

            st.write("勤務先:", record["workplace"])
            st.write("勤務日:", record["work_date"])
            st.write("開始時間:", record["start_time"])
            st.write("終了時間:", record["end_time"])
            st.write("休憩時間:", record["break_minutes"])
            st.write("時給:", record["hourly_wage"])
            st.write("給与:", record["salary"])
            st.write("振込日:", record["pay_date"])

        elif event_type == "pay":

            st.subheader("給与振込詳細")

            st.write("勤務先:", record["workplace"])
            st.write("勤務日:", record["work_date"])
            st.write("振込予定額:", record["salary"])

        elif event_type == "expense":

            st.subheader("支出詳細")

            st.write("項目:", record["purpose"])
            st.write("メモ:", record.get("memo", ""))
            st.write("使用日:", record["due_date"])
            st.write("金額:", record["amount"])

        # 削除機能
    st.write("---")
    
    record_id = record["id"]
    delete_key = f"delete_confirm_{event_type}_{record_id}"    

    if not st.session_state.get(delete_key, False):

        if st.button("削除", key=f"delete_button_{event_type}_{record_id}"):

            st.session_state[delete_key] = True
            st.rerun()

    else:

        st.warning("本当に削除しますか？")

        col1, col2 = st.columns(2)

        with col1:

            if st.button("削除を確定", key=f"confirm_{event_type}_{record_id}"):

                delete_data(event_type, record_id)

                st.session_state[delete_key] = False

                st.success("削除しました！")

                st.rerun()

        with col2:

            if st.button("キャンセル", key=f"cancel_{event_type}_{record_id}"):

                st.session_state[delete_key] = False

                st.rerun()


#calendar_state = st_calendar(events = calendar_events ,options={"firstDay": 1},callbacks=["eventClick","dateClick","viewDidMount"],key="calendar")
calendar_state = st_calendar(
    events=calendar_events,
    options={
        "firstDay": 1,
        "initialDate": f"{target_month}-01"
    },
    callbacks=["eventClick"],
    key=f"calendar_{target_month}")
#0：日曜,1：月曜
 #callbacks=["eventClick"]：イベントをクリックしたときの情報を取得する。
 #calendar_state：クリックされたイベントの情報を受け取る

###-----イベントの判定はカレンダー側、表示内容の決定は関数側-----###
# イベントクリック時の処理
if calendar_state and calendar_state.get("callback") == "eventClick":

    clicked_event = calendar_state["eventClick"]["event"]
    clicked_id = clicked_event["id"]
    if st.session_state.get("last_clicked_id") == clicked_id:
        st.stop()
    st.session_state["last_clicked_id"] = clicked_id

    # シフトがクリックされた場合
    if clicked_id.startswith("shift_"):

        shift_id = clicked_id[len("shift_"):]

        shift = next((s for s in shifts if s["id"] == shift_id),None)

        if shift is not None:
            show_event_detail("shift", shift)


    # 給与日がクリックされた場合
    elif clicked_id.startswith("salary_"):
        parts = clicked_id.split("_", 2)

        workplace = parts[1]
        pay_date = parts[2]

        total_salary = sum(shift["salary"]
                           for shift in shifts
                           if shift["workplace"] == workplace
                           and shift["pay_date"] == pay_date)

        @st.dialog("給与詳細")
        def show_salary():
            st.subheader(f"{workplace}給与")
            st.write("振込日:", pay_date)
            st.write("合計給与:", f"{total_salary}円")
        show_salary()


    # 支出がクリックされた場合
    elif clicked_id.startswith("expense_"):

        expense_id = clicked_id[len("expense_"):]

        expense = next((e for e in expenses if e["id"] == expense_id),None)

        if expense is not None:
            show_event_detail("expense", expense)

tab1, tab2, tab3, tab4 = st.tabs(["ホーム","シフト","支出","設定"])

#ホーム画面
with tab1:

    #収支計算
    st.subheader("収支計算")

    st.markdown(
    f"""
    <div style="
        background-color:{balance_color};
        padding:25px;
        border-radius:15px;
        text-align:center;
        margin-bottom:20px;
    ">
        <h3>予想残高</h3>
        <h1>{future_balance:,}円</h1>
    </div>
    """,
    unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
        f"""
        <div style="
        background-color:#dbeafe;
        padding:15px;
        border-radius:10px;
        text-align:center;
        ">
        <h4>収入</h4>
        <h3>{monthly_income:,}円</h3>
        </div>
        """,
        unsafe_allow_html=True)

    with col2:
        st.markdown(
        f"""
        <div style="
        background-color:#fee2e2;
        padding:15px;
        border-radius:10px;
        text-align:center;
        ">
        <h4>支出</h4>
        <h3>{monthly_expense:,}円</h3>
        </div>
        """,
        unsafe_allow_html=True)

    with col3:
        st.markdown(
        f"""
        <div style="
        background-color:#dcfce7;
        padding:15px;
        border-radius:10px;
        text-align:center;
        ">
        <h4>収支</h4>
        <h3>{balance:,}円</h3>
        </div>""",unsafe_allow_html=True)

    st.subheader("労働時間不足")
    if balance<0:
        for workplace in list(WORKPLACES.keys()):
            hourly_wage = WORKPLACES[workplace]["hourly_wage"]  
            if hourly_wage > 0:
                required_hours = abs(balance) / hourly_wage
                color = WORKPLACES[workplace]["color"]
                st.markdown(f"<span style='color:{color}'>"f"勤務地:{workplace}"f"</span>",unsafe_allow_html=True)
                st.write(f"必要なシフト: {required_hours:.1f}時間")
    else:
        st.write(f"必要なシフト: ないです")

    current_balance = st.number_input("現在残高",value=current_balance)
    if st.button("残高更新"):
        save_balance(current_balance)
        st.success("保存しました")

#シフト入力専用画面
with tab2:
    st.subheader("登録済みシフト")
    st.metric("収入予定",f"{monthly_income}円")
    for wp in list(WORKPLACES.keys()):
        st.write(f"{wp}の収入:"f"{workplace_incomes[wp]}円")
    #シフト入力
    workplace = st.selectbox("勤務先",list(WORKPLACES.keys()))
    work_date = st.date_input("勤務日")
    start_time_input = st.time_input("開始時間",value=datetime.strptime("09:00", "%H:%M").time())
    end_time_input = st.time_input("終了時間",value=datetime.strptime("17:00", "%H:%M").time())
    break_minutes = st.selectbox("休憩時間",[0,15,30,45,60])
    hourly_wage = WORKPLACES[workplace]["hourly_wage"]

    #給与計算/登録
    start_time = (start_time_input.hour+ start_time_input.minute / 60)
    end_time = (end_time_input.hour+ end_time_input.minute / 60)
    work_hours = (end_time - start_time)  - (break_minutes / 60)
    if work_hours <= 0:
        st.write("エラー")
        salary = 0
    salary = int(work_hours * hourly_wage)

    pay_date = calculate_pay_date(work_date,workplace)

    st.write('振り込み日',f"{pay_date}")
    st.write('給料',f"{salary}")
    
    #登録ボタンの表示
    register1 = st.button("シフト登録")

    #ボタン押されたら実行
    if register1:
        new_shifts = {"id": str(uuid.uuid4()),"workplace": workplace, "work_date": str(work_date), "pay_date": str(pay_date), "start_time": start_time, "end_time": end_time, "break_minutes": break_minutes, "hourly_wage": hourly_wage, "salary":salary}

        shifts = load_shifts()
        save_shift(new_shifts)
        
        st.write("登録しました")
    
    sorted_shifts = sorted([s for s in shifts
                           if s["work_date"][:7] == target_month],
                           key=lambda x: x["work_date"],reverse=True)
    current_date = None
    
    for shift in sorted_shifts:
    # 日付が変わったら見出し表示
        if shift["work_date"] != current_date:
            current_date = shift["work_date"]
            st.divider()
            st.markdown(f"## 📅 {current_date}")
        
        color = WORKPLACES[shift["workplace"]]["color"]
        work_hours = (shift["end_time"] - shift["start_time"] - shift["break_minutes"] / 60)

        with st.container(border=True):
            st.markdown(f"<span style='color:{color}; font-size:20px;'>"f"{shift['workplace']}"f"</span>",unsafe_allow_html=True)
            st.write(f"⏰ {float_to_time(shift['start_time'])}"f" ～ "f"{float_to_time(shift['end_time'])}")
            st.write(f"🕒 {work_hours:.1f}時間勤務")
            st.write(f"💰 {shift['salary']}円")
            st.write(f"振込日：{shift['pay_date']}")
            
            shift_id = shift["id"]
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("編集",key=f"edit_shift_{shift_id}"):
                                show_event_detail("shift",shift)
            with col2:
                if st.button("削除",key=f"delete_{shift_id}"):
                                delete_shift(shift_id)
                                st.rerun()   
    
#出費入力専用画面
with tab3:
    st.subheader("登録済み支出")
    st.metric("対象月の支出予定総額",f"{monthly_expense}円")
    
    sorted_expenses = sorted([e for e in expenses
                           if e["due_date"][:7] == target_month],
                           key=lambda x: x["due_date"],reverse=True)
    current_date = None
    
    #出費入力
    st.subheader("新規支出登録")
    due_date = st.date_input("使用日")
    memo = st.text_input("メモ")
    amount = st.number_input("料金",min_value=0,step=100)

    expense_options = {
        "🍽️ 食費": "食費",
        "🚃 交通費": "交通費",
        "🏀 部活関連": "部活関連",
        "💗 交際費": "交際費",
        "👕 ファッション": "ファッション",
        "✂️ ヘアケア": "ヘアケア",
        "🧖 スキンケア": "スキンケア",
        "💊 医療": "医療",
        "⭐ 遊び": "遊び",
        "🧼 日用品": "日用品",
        "✏️ 勉強": "勉強",
        "🧳 旅行": "旅行",
        "✨ その他": "その他"}
    selected_display = st.pills("カテゴリー",list(expense_options.keys()),selection_mode="single")
    if selected_display:
        purpose = expense_options[selected_display]

    register2 = st.button("支出登録",use_container_width=True)

    if register2:
        if not purpose:
            st.error("カテゴリーを選択してください")
        else:
            new_expenses = {"id": str(uuid.uuid4()),"purpose": purpose,"memo": memo,"due_date": str(due_date),"amount": int(amount)}
            expenses = load_expenses()
            save_expense(new_expenses)
            st.success("登録しました")

    st.subheader("登録済み支出")
    for expense in sorted_expenses:
        # 日付が変わったら見出し表示
        if expense["due_date"] != current_date:
            current_date = expense["due_date"]
            st.divider()
            st.markdown(f"## 📅 {current_date}")

        color = EXPENSES_COLORS[expense["purpose"]]
        with st.container(border=True):
            st.markdown(f"<span style='color:{color}; font-size:20px;'>"f"{expense['purpose']}"f"</span>",unsafe_allow_html=True)
            
            if expense.get("memo"):
                st.write(f"📝 {expense['memo']}")
            st.write(f"💰 {expense['amount']}円")
            
            expense_id = expense["id"]
            col1, col2 = st.columns(2)
            with col1:
                if st.button("編集",key=f"edit_expense_{expense_id}"):
                    show_event_detail("expense",expense)
            with col2:
                if st.button("削除",key=f"expense_delete_{expense_id}"):
                    delete_expense(expense_id)
                    st.rerun()


with tab4:
    
    ###-------------
    #WORKPLACES操作
    ###-------------
    st.subheader("勤務先一覧")

    #削除
    for workplace in list(WORKPLACES.keys()):
        st.write(workplace)
        if st.button("削除",key=f"delete_workplace_{workplace}"):

            del WORKPLACES[workplace]
            save_master(WORKPLACES,EXPENSES_COLORS)
            st.rerun()

    #編集
    selected_workplace = st.selectbox("編集する勤務先",list(WORKPLACES.keys()))
    current = WORKPLACES[selected_workplace]
    hourly_wage = st.number_input("時給",value=current["hourly_wage"])
    color_wk = st.color_picker("色",value=current["color"],key="edit_workplace_color")
    
    if st.button("勤務先更新"):
        WORKPLACES[selected_workplace] = {"hourly_wage": hourly_wage,"closing_day": current["closing_day"],"pay_day": current["pay_day"],"color": color_wk}
        save_master(WORKPLACES,EXPENSES_COLORS)
        st.success("更新しました")

    #追加
    workplace_name = st.text_input("勤務先名")
    hourly_wage = st.number_input("時給")
    workplace_color = st.color_picker("色",key="workplace_color")
    register_workplace = st.button("勤務先追加")
    if register_workplace:
        if workplace_name.strip() == "":
            st.error("勤務先名を入力してください")
        elif hourly_wage <= 0:
            st.error("時給を入力してください")
        else:           
            WORKPLACES[workplace_name] = {"hourly_wage": hourly_wage,"closing_day": 20,"pay_day": 5,"color": workplace_color}
            save_master(WORKPLACES,EXPENSES_COLORS)
            st.success("追加しました")


    ###----------------------
    #EXPENSES_COLORS操作
    ###----------------------
    st.subheader("支出項目一覧")

    #削除
    for purpose in list(EXPENSES_COLORS.keys()):
        st.write(purpose)
        if st.button("削除",key=f"delete_expense_{purpose}"):
            del EXPENSES_COLORS[purpose]
            save_master(WORKPLACES,EXPENSES_COLORS)
            st.rerun()

    #編集
    selected_expenses = st.selectbox("編集する支出項目",list(EXPENSES_COLORS.keys()))
    current = EXPENSES_COLORS[selected_expenses]
    color_ex = st.color_picker("色",value = current,key="edit_expense_color")

    if st.button("支出更新"):
        EXPENSES_COLORS[selected_expenses] = color_ex
        save_master(WORKPLACES,EXPENSES_COLORS)
        st.success("更新しました")
    
    #追加
    purpose = st.text_input("項目")
    expense_color = st.color_picker("色",key="expense_color")
    register_expense = st.button("支出追加")
    if register_expense:
        EXPENSES_COLORS[purpose] = expense_color
        save_master(WORKPLACES,EXPENSES_COLORS)
        st.success("追加しました")

with st.expander("カラーパレット"):
    st.subheader("カラーパレット一覧")
    # 勤務先カラー
    for workplace, info in WORKPLACES.items():
        st.markdown(f"<span style='color:{info['color']}; "f"font-weight:bold; "f"font-size:18px;'>■</span> "f"{workplace}",unsafe_allow_html=True)
    # 支出カラー
    for purpose, color in EXPENSES_COLORS.items():
        st.markdown(f"<span style='color:{color}; "f"font-weight:bold; "f"font-size:18px;'>■</span> "f"{purpose}",unsafe_allow_html=True)
    # 給料日カラー
    st.markdown("<span style='color:gold; ""font-weight:bold; ""font-size:18px;'>■</span> ""給料日",unsafe_allow_html=True)

