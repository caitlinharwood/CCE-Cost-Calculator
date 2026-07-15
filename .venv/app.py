import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import math

st.title("CCE Cost Calculator")
st.subheader("Cumulative 20-year spending comparison for current system vs fixed solar vs solar tracking options")

#constants
tracker_kw = 42.84
itc_rate = 0.30
degrad = 0.005
om_per_kw = 20.0     
om_esc = 0.04
total_yrs = 20
years = list(range(1,total_yrs + 1))
macrs_rates = [0.20, 0.32, 0.192, 0.1152, 0.1152, 0.0576]
base_panel = 1.10
machinery_cost = 6500.00
com_costs = 1507
excess_credit_rate = 0.85
inverter_rate = 0.12
kwh_kw_yr_tracker = 2360
kwh_kw_yr_fixed = 1680
elecbos_w = 0.18
labor_rate = 85
labor_hours = 1595.06
acc_cost = 0.02
strucural = 48115
mod_per_tracker = 90
complexity = 1.08


#get user inputs
st.sidebar.subheader("Inputs:")
roof_size=st.sidebar.number_input("Area of roof (sq ft): ")
roof_percent=st.sidebar.slider("Percentage of roof covered: ", 10,100)
roof_dec = float(roof_percent) / 100
disc_rate=st.sidebar.slider("Discount rate (%):",min_value=0.0, max_value=15.0, value=7.0, step=0.5) / 100
sdge_rate = st.sidebar.selectbox("Rate Plan",["SDG&E TOU-A", "SDG&E AL-TOU", "SDG&E AL-TOU-2", "SDG&E TOU-DR2", "SDG&E AL-TOU-L", "SDG&E DG-R-L", "SDG&E TOU-M", "SDG&E AL-TOU-M", "SDG&E DG-R-M", "SDG&E TOU-A2", "SDG&E TOU-A3"])
rate_mapping = {
    "SDG&E TOU-A": [0.57574,0.42312,0.43513,0.33589],   #summer_peak, summer_offpeak, winter_peak, winter_offpeak
    "SDG&E AL-TOU": [0.242, 0.151, 0.132, 0.264, 0.154, 0.121], #sum_peak, sum_offpeak, sum_sop, winter_peak, winter_offpeak, winter_sop, off p  sop
    "SDG&E AL-TOU-2": [0.2586, 0.16378, 0.14437, 0.28212, 0.16654, 0.13301],  #sum_peak, sum_offpeak, sum_sop, winter_peak, win_offpeak, win)sop
    "SDG&E TOU-DR2": [0.68907, 0.41773, 0.61014, 0.47316], #sum_peak, sum_offpeak, winter_peak, winter_offpeak
    "SDG&E AL-TOU-L": [0.28315,0.17847, 0.15744, 0.30956, 0.18192, 0.1449], #sum_peak, offpeak, sop, winter_peak, offpeak, sop
    "SDG&E DG-R-L": [0.16417, 0.29004, 0.18206, 0.7732, 0.20089, 0.17241],
    "SDG&E TOU-M": [0.6229,0.30936, 0.23389, 0.3332, 0.24944, 0.22592],
    "SDG&E AL-TOU-M": [0.31908, 0.20971, 0.1879, 0.34686, 0.21349, 0.1748],
    "SDG&E DG-R-M": [0.96824, 0.27714, 0.16457, 0.56019, 0.18424, 0.15449],
    "SDG&E TOU-A2": [0.64136, 0.34408, 0.27545, 0.36934, 0.2903, 0.26697],
    "SDG&E TOU-A3": [0.57911, 0.44639, 0.32795, 0.42062, 0.34158, 0.31825]

}

#summer: june 1 - oct 31
#winter: nov 1 - may 31

#peak: 4pm - 9pm
#off-peak: 6am - 10am, 2pm - 4pm, 9pm - 12am
#super off-peak: 12am - 6am, 10am - 2pm

elec_current = rate_mapping[sdge_rate]

#% increase per year
elec_increase_input = st.sidebar.slider("Rate increase per year (%):",0,15,5)                                   
elec_increase = float(elec_increase_input) / 100

fed_tax_input = st.sidebar.slider("Federal tax rate:", 0,40,30) 
fed_tax = float(fed_tax_input) / 100                                                             

used_area = roof_size * roof_dec
system_size_f = used_area / 15            #capacity in kW

if roof_size:
    num_trackers_rec = max(1, round(system_size_f / tracker_kw))
else:
    num_trackers_rec = 10
num_trackers = st.sidebar.slider("Number of trackers:", 1, 50, num_trackers_rec)
system_size_t = num_trackers * tracker_kw
system_size = system_size_f

loan = st.sidebar.checkbox("Payment Over Time with Loan?")
if loan:
    loan_length = st.sidebar.slider("Length of time for loan (years):",0,20)
    loan_interest_input = st.sidebar.slider("Annual Interest Rate:",0,30,15)
    loan_interest = loan_interest_input / 100
    monthly_payment = st.sidebar.number_input("Desired monthly payment amount:")
else:
    st.sidebar.write("Payment added to upfront costs.")
 
#gross cost baseline
fixed_gross_per_w = 1.54
tracker_gross_per_w = 2.50

#upfront costs
fixed_cap = (system_size_f * 1000 * base_panel) + com_costs
tracker_cap = (system_size_t * 1000 * base_panel) + (num_trackers * machinery_cost) + com_costs

fixed_itc_value = fixed_cap * itc_rate
tracker_itc_value = tracker_cap * itc_rate

fixed_net_inv = fixed_cap - fixed_itc_value
tracker_net_inv = tracker_cap - tracker_itc_value

uploaded_file = st.file_uploader("Please upload a CSV file of your Green Button Data:", type=["csv"])

#get csv info
if uploaded_file is not None:
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file)

    all_columns = [str(col).strip() for col in df.columns]
    col_index = 0
    for i, col in enumerate(all_columns):
        col_lower = col.lower()
        if 'usage' in col_lower or 'kwh' in col_lower or 'net' in col_lower or 'value' in col_lower:
            col_index = i
            break
    target_column = st.selectbox(
        "Please select the column that contains your electricty consumption data:",
        options = all_columns,
        index = col_index
    )

    for i, col in enumerate(all_columns):
        col_lower = col.lower()
        if 'start' in col_lower:
            col_index = i
            break
    target_column_date = st.selectbox(
        "Please select the column that contains the date:",
        options = all_columns,
        index = col_index
    )

    #elec_current = float(elec_current_input)
    fixed_sp_yield = 1450
    tracker_sp_yield = 1900
    baseline_trend = []
    fixed_trend = []
    tracker_trend = []
    baseline_trend_pv = []
    fixed_trend_pv = []
    tracker_trend_pv = []

    #set baseline
    cash_flow_base = 0.0
    cash_flow_base_pv = 0.0
    cf_fixed = fixed_net_inv
    cf_tracker = tracker_net_inv
    cf_fixed_pv = fixed_net_inv
    cf_tracker_pv = tracker_net_inv

    raw_usage = pd.to_numeric(df[target_column], errors = 'coerce').dropna()

    #15 min or hourly intervals
    if len(raw_usage) > 15000:
        usage = raw_usage.head(35040)
        total_baseline_kwh = usage.sum() / 4.0

    else:
        usage = raw_usage.head(8760)
        total_baseline_kwh = usage.sum()

    usage_data = pd.to_datetime(df[target_column_date], format='%m/%d/%Y %I:%M/%S %p', errors = 'coerce').dropna()
    month = df[usage_data].dt.month
    hour = df[usage_data].dt.hour

    sum_peak_cond = (month.isin([6,7,8,9,10])) & ((hour >=16) & (hour <=21))
    sum_offpeak_cond = (month.isin([6,7,8,9,10])) & (((hour >= 6) & (hour <=10)) | ((hour >= 14) & (hour < 16)) | hour > 21)
    sum_soffpeak_cond = (month.isin([6,7,8,9,10])) & ((hour < 6) | ((hour >= 10) & (hour < 14)))

    win_peak_cond = (month.isin([1,2,3,4,5,11,12])) & ((hour >=16) & (hour <=21))
    win_offpeak_cond = (month.isin([1,2,3,4,5,11,12])) & (((hour >= 6) & (hour <=10)) | ((hour >= 14) & (hour < 16)) | hour > 21)
    win_soffpeak_cond = (month.isin([1,2,3,4,5,11,12])) & ((hour < 6) | ((hour > 10) & (hour < 14)))

    conditions = [
        sum_peak_cond,
        sum_offpeak_cond,
        sum_soffpeak_cond,
        win_peak_cond,
        win_offpeak_cond,
        win_soffpeak_cond
    ] 

    elec_options = [
        elec_current[0],
        elec_current[1],
        elec_current[2],
        elec_current[3],
        elec_current[4],
        elec_current[5],
    ]

    df['elec_current_val'] = np.select(conditions, elec_options, default = np.nan)


    #summer: june 1 - oct 31
    #winter: nov 1 - may 31

    #peak: 4pm - 9pm
    #off-peak: 6am - 10am, 2pm - 4pm, 9pm - 12am
    #super off-peak: 12am - 6am, 10am - 2pm

    target_cap_kw = num_trackers * tracker_kw

    fixed_raw_gen = system_size_f * fixed_sp_yield
    tracker_raw_gen = system_size_t * tracker_sp_yield

    #fixed calculations
    fixed_yearly = target_cap_kw * 1350
    fixed_itc = fixed_cap * itc_rate
    fixed_basis = fixed_cap - (fixed_itc * 0.5)
    fixed_mac = [round(fixed_basis * r * fed_tax) for r in macrs_rates]
    num_modules_f = round((total_baseline_kwh * 1000) / (435 * 1680))
    pv_modules_f = num_modules_f * base_panel
    inverter_f = 0.12 * (435 * num_modules_f)
    electrical_bos_cost = elecbos_w * 1000 * pv_modules_f
    labor_cost = labor_rate * labor_hours
    acc_total = acc_cost * (435 * num_modules_f)
    fixed_upfront = pv_modules_f + inverter_f + electrical_bos_cost + labor_cost + acc_total

    #tracker calculations
    tracker_yearly = target_cap_kw * (1350 * 1.25)
    tracker_itc = tracker_cap * itc_rate
    tracker_basis = tracker_cap - (tracker_itc * 0.5)
    tracker_mac = [round(tracker_basis * r * fed_tax) for r in macrs_rates]
    kw_dc = 435 * complexity
    target_sys_t = total_baseline_kwh * 1000 / (kw_dc * kwh_kw_yr_tracker)
    num_modules_t = (total_baseline_kwh / (0.435 * 2360))
    num_trackers_rec = math.ceil(num_modules_t / mod_per_tracker)
    new_t_rec = st.sidebar.write("Recommended: ,{new_t_rec}, trackers")
    pv_modules_t = num_modules_t * base_panel
    inverter_t = inverter_rate * target_sys_t * 1000
    mounting = 233600
    struc_t = 15360
    elecbos_t = elecbos_w * target_sys_t * 1000
    acc_total_t = acc_cost * target_sys_t
    tracker_upfront = pv_modules_t + inverter_t + mounting + struc_t + labor_cost + acc_total_t

    ann_baseline_spending = total_baseline_kwh * elec_current

    cash_flow_base = 0.0

    fixed_ann_savings = []
    tracker_ann_savings = []

    for i in range(total_yrs):
        yr_num = i + 1

        if loan:
            yearly_payment_f = fixed_upfront * ((loan_interest * (1 + loan_interest) ** loan_length)) / (((1 + loan_interest) ** loan_length) - 1)
            yearly_payment_t = tracker_upfront * ((loan_interest * (1 + loan_interest) ** loan_length)) / (((1 + loan_interest) ** loan_length) - 1)

        else:
            if i == 1:
                yearly_payment_f = fixed_upfront
                yearly_payment_t = tracker_upfront
            else:
                yearly_payment_f = 0
                yearly_payment_t = 0

        #rising rates
        utility_escalation_factor = (1 + elec_increase) ** i  #utlity increase
        om_escalation_factor = (1 + om_esc) ** i       # 4% O&M Escalation
        panel_eff = (1 - degrad) ** i
        disc_factor = 1 / ((1 + disc_rate) ** (i + 1))

        #current baseline
        current_spending = total_baseline_kwh * elec_current * utility_escalation_factor
        cash_flow_base += current_spending
        cash_flow_base_pv += current_spending * disc_factor 
        baseline_trend.append(cash_flow_base)
        baseline_trend_pv.append(cash_flow_base_pv)
        
        f_macrs_cred = fixed_mac[i] if i < len(fixed_mac) else 0
        t_macrs_cred = tracker_mac[i] if i < len(tracker_mac) else 0

        #fixed
        fixed_gen = system_size_f * fixed_sp_yield * panel_eff

        if fixed_gen <= total_baseline_kwh:
            fixed_gen_usable = fixed_gen
        else:
            excess_f = fixed_gen - total_baseline_kwh
            fixed_gen_usable = total_baseline_kwh + excess_f * excess_credit_rate

        fixed_offset = fixed_gen_usable * elec_current * utility_escalation_factor      #fixed utility savings
        fixed_remaining = max(0.0,current_spending - fixed_offset)
        fixed_om = (system_size_f * om_per_kw) * om_escalation_factor
        fixed_out_of_pocket = fixed_remaining + fixed_om - f_macrs_cred + fixed_yearly
        
        #net fixed
        cf_fixed += fixed_out_of_pocket
        fixed_trend.append(cf_fixed)
        cf_fixed_pv += fixed_out_of_pocket * disc_factor
        fixed_trend_pv.append(cf_fixed_pv)
        
        #tracker
        tracker_gen = system_size_t * tracker_sp_yield * panel_eff

        if tracker_gen <= total_baseline_kwh:
            tracker_gen_usable = tracker_gen
        else:
            excess_t = tracker_gen - total_baseline_kwh
            tracker_gen_usable = total_baseline_kwh + excess_t * excess_credit_rate
        tracker_offset = tracker_gen_usable * elec_current * utility_escalation_factor
        tracker_remaining = max(0.0,current_spending - tracker_offset)
        tracker_om = (system_size_t * om_per_kw * 1.25) * om_escalation_factor 
        
        #net tracker
        tracker_out_of_pocket = tracker_remaining + tracker_om - t_macrs_cred + tracker_yearly
        cf_tracker += tracker_out_of_pocket
        tracker_trend.append(cf_tracker)
        cf_tracker_pv += tracker_out_of_pocket * disc_factor
        tracker_trend_pv.append(cf_tracker_pv)

        fixed_ann_savings.append(fixed_offset - fixed_om + f_macrs_cred)
        tracker_ann_savings.append(tracker_offset - tracker_om + t_macrs_cred)

        disc_factor = (1 + disc_rate) ** i


    target_len = len(years)

    use_pv = st.checkbox(
        "Discount cash flows to present value",
        value = True,
    )

    if use_pv:
        chart_baseline, chart_fixed, chart_tracker = baseline_trend_pv, fixed_trend_pv, tracker_trend_pv
        y_axis_title = "Present Value of Cumulative Spending ($)"
        chart_title = "20-Year Cumulative Spending (Present Value)"
    else:
        chart_baseline, chart_fixed, chart_tracker = baseline_trend, fixed_trend, tracker_trend
        y_axis_title = "Cumulative Spending ($)"
        chart_title = "20-Year Cumulative Spending"
    #line graphs
    chart_data = pd.DataFrame({
        "Year": years,
        "Current": chart_baseline,
        "Fixed": chart_fixed,
        "Tracking": chart_tracker,
    })

    #break-even points
    break_even_f = None
    for yr in years:
        fidx = yr -1
        if fidx == 0:
            continue
        if chart_baseline[fidx] >= chart_fixed[fidx] and chart_baseline[fidx - 1] < chart_fixed[fidx - 1]:
            fprev_yr = years[fidx - 1]
            fprev_dif = chart_fixed[fidx - 1] - chart_baseline[fidx - 1]
            fcurrent_dif = chart_baseline[fidx] - chart_fixed[fidx]
            fdif = fprev_dif / (fprev_dif + fcurrent_dif)
            break_even_f = round(fprev_yr + fdif, 2)
            break
    
    break_even_t = None
    for yr in years:
        tidx = yr -1
        if tidx == 0:
            continue
        if chart_baseline[tidx] >= chart_tracker[tidx] and chart_baseline[tidx - 1] < chart_tracker[tidx - 1]:
            tprev_yr = years[tidx - 1]
            tprev_dif = chart_tracker[tidx - 1] - chart_baseline[tidx - 1]
            tcurrent_dif = chart_baseline[tidx] - chart_tracker[tidx]
            tdif = tprev_dif / (tprev_dif + tcurrent_dif)
            break_even_t = round(tprev_yr + tdif, 2)
            break
    
    #chart labels
    fig = px.line(
        chart_data,
        x=chart_data["Year"],
        y=[chart_data["Current"], chart_data["Fixed"], chart_data["Tracking"]],
        labels = {"Spending": "Cumulative Spending ($)", "variable": "Scenario"},
        title = "20-Year Cumulative Spending"
    )

    if break_even_f is not None:
        fig.add_vline(
            x = break_even_f,
            line_dash = "dash",
            line_color = "lightskyblue",
            line_width = 1,
        )
        fig.add_annotation(
            x = break_even_f,
            y = max(baseline_trend) * 0.85,
            text = f"Fixed Break-Even Year: {break_even_f}",
            showarrow = False,
            font = dict(color = "black", size = 11)
        )

    if break_even_t is not None:
        fig.add_vline(
            x = break_even_t,
            line_dash = "dash",
            line_color = "red",
            line_width = 1
        )
        fig.add_annotation(
            x = break_even_t,
            y = max(baseline_trend),
            text = f"Tracker Break-Even Year: {break_even_t}",
            showarrow = False,
            font = dict(color = "black", size = 11)
        )
    
    fig.update_layout(
        xaxis = dict(tickmode = 'linear', tick0 = 1, dtick = 1, title = "Year"),
        yaxis = dict(title = "Spending ($)"),
        hovermode = "closest"
    )

    st.plotly_chart(fig, use_container_width = True)

    #savings chart
    savings_data = pd.DataFrame({
        #higher w tax benefits, finance over time
        "Year": years,
        "Fixed Solar Savings": fixed_ann_savings,
        "Tracker Solar Savings": tracker_ann_savings
    })

    fig_bar = px.bar(
        savings_data,
        x = "Year",
        y = ["Fixed Solar Savings", "Tracker Solar Savings"],
        barmode = "group",
        labels = {"value": "Annual Net Savings ($)", "variable": "Option"},
        title = "Annual Savings Comparison"
    )
    fig_bar.update_layout(
        xaxis = dict(tickmode = 'linear', tick0 = 1, dtick = 1, title = "Year"),
        yaxis = dict(title = "Savings ($ / Year)")
        #hovermode = "x unified"
    )
    st.plotly_chart(fig_bar, use_container_width = True)


else:
    st.write("Please upload a CSV file of your Green Button Data.")

