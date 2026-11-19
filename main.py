#完成版
import json

mode = input("新規入力なら１or保存データ読込なら２:",)

if mode == '1':
    
    ##A データ取得
    target_month = input("確認したい月を入力して(例:2026-11):")
    
    #シフト情報入力ループ
    shifts = []
    while True:
        workplace = input("勤務地（終了する場合は「なし」と入力）:")
        if workplace == "なし":
            break
        work_date = input("勤務日:")
        pay_date = input("支払日:")
    
        # 時間や時給など、後で計算に使うものは int() で数値に変換しておく
        start_hour = int(input("勤務開始時間:"))
        end_hour = int(input("勤務終了時間:"))
        break_minutes = int(input("休憩時間（分）:"))
        hourly_wage = int(input("時給（円）:"))
    
        # 入力されたデータを辞書としてまとめ、リストに追加する
        shift_info = {"workplace": workplace, 
                      "work_date": work_date, 
                      "pay_date": pay_date,
                      "start_hour": start_hour, 
                      "end_hour": end_hour, 
                      "break_minutes": break_minutes, 
                      "hourly_wage": hourly_wage}
    
        shifts.append(shift_info)

    print("入力が終了しました")

    #出費情報入力ループ
    expenses = []
    while True:
        name = input("利用法（終了する場合は「なし」と入力）:")
    
        if name == "なし":
            break
        
        due_date = input("支払日:")
        amount = int(input("金額（円）:"))
        
        expense_info = {"name": name,
                        "due_date": due_date,
                        "amount": amount,}
        
        expenses.append(expense_info)

    print("入力が終了しました")

    ##B データ保存
    def save_data(shifts, expenses):
        data = {"shifts": shifts,
                "expenses": expenses}
        with open("data.json", "w", encoding="utf-8") as file:
            json.dump(data,file,ensure_ascii=False,indent=4)
            
            print("保存しました")
    
    #呼び出し（必要か不明）
    save_data(shifts, expenses)

elif mode == '2':

    target_month = input("確認したい月を入力して(例:2026-11):")
    ##C データの読み込み
    def load_data():
        with open("data.json", "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    data = load_data()
    shifts = data["shifts"]
    expenses = data["expenses"]

#print("シフト:",shifts)
#print("出費:",expenses)

##D 関数を定義

#各シフトにおける給料の計算
def calculate_salary(shifts):
    for shift in shifts:
        start_hour = shift["start_hour"]
        end_hour = shift["end_hour"]
        break_minutes = shift["break_minutes"]
        hourly_wage = shift["hourly_wage"]
        
        work_hours = (end_hour - start_hour) - (break_minutes / 60)
        if work_hours <= 0:
            print("エラー")
            return 0
        
        salary = int(work_hours * hourly_wage)
        shift["salary"] = salary
        
        print(f"勤務地:{shift['workplace']}")
        print(f"振込月:{shift['pay_date'][5:7]}月")
        print(f"給与:{shift["salary"]}円")
    return salary
#当月の月収の計算
def calculate_monthly_income(shifts,target_month):
    monthly_income = 0
    #calculate_salary(shifts)
    for shift in shifts:
        if target_month == shift["pay_date"][0:7]:
            monthly_income = monthly_income + shift["salary"]
        else:
            monthly_income = monthly_income
    
    print(f"{target_month[5:7]}月の収入予定: {monthly_income}円")
    return monthly_income
#当月の支出
def calculate_monthly_expense(expenses,target_month):
    monthly_expense = 0
    for expense in expenses:
        if target_month == expense["due_date"][0:7]:
            monthly_expense = monthly_expense + expense["amount"]
            print(f"利用先:{expense['name']}")
            print(f"金額:{expense["amount"]}円")
        else:
            monthly_expense = monthly_expense

    print(f"{target_month[5:7]}月の支出予定: {monthly_expense}円")
    return monthly_expense
#当月の不足額
def calculate_balance(monthly_income, monthly_expense, target_month):
    balance = monthly_income - monthly_expense
    print(f"{target_month[5:7]}月の収支: {balance}円")

    if balance<0:
        hourly_wage = 1200
        required_hours = abs(balance)/hourly_wage
        print(f"必要なシフト: {required_hours:.1f}時間")
    else:
        print(f"必要なシフト: ないです")

    return 
##E ４情報(その月の収入、その月の支出、差額、不足分の労働時間)の出力
calculate_salary(shifts)
monthly_income = calculate_monthly_income(shifts,target_month)
monthly_expense = calculate_monthly_expense(expenses,target_month)
calculate_balance(monthly_income, monthly_expense, target_month)