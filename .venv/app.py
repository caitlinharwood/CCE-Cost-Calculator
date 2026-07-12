import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

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

#get user inputs
st.sidebar.subheader("Inputs:")
roof_size=st.sidebar.number_input("Area of roof (sq ft): ")
roof_percent=st.sidebar.slider("Percentage of roof covered: ", 10,100)
roof_dec = float(roof_percent) / 100
disc_rate=st.sidebar.slider("Discount rate (%):",min_value=0.0, max_value=15.0, value=7.0, step=0.5) / 100
sdge_rate = st.sidebar.selectbox("Rate Plan",["SDG&E TOU-A", "SDG&E AL-TOU", "SDG&E AL-TOU-2", "SDG&E TOU-DR2", "SDG&E AL-TOU-L", "SDG&E DG-R-L", "SDG&E TOU-M", "SDG&E AL-TOU-M", "SDG&E DG-R-M", "SDG&E TOU-A2", "SDG&E TOU-A3"])
rate_mapping = {
    "SDG&E TOU-A": 0.3150,
    "SDG&E AL-TOU": 0.1600,
    "SDG&E AL-TOU-2": 0.1720,
    "SDG&E TOU-DR2": 0.3650,
    "SDG&E AL-TOU-L": 0.1550,
    "SDG&E DG-R-L": 0.1850,
    "SDG&E TOU-M": 0.2850,
    "SDG&E AL-TOU-M": 0.1650,
    "SDG&E DG-R-M": 0.2100,
    "SDG&E TOU-A2": 0.3320,
    "SDG&E TOU-A3": 0.2980
}
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

    target_cap_kw = num_trackers * tracker_kw

    fixed_raw_gen = system_size_f * fixed_sp_yield
    tracker_raw_gen = system_size_t * tracker_sp_yield

    fixed_usable_per = 0.85 if fixed_raw_gen > total_baseline_kwh else 1.0
    tracker_usable_per = 0.70 if tracker_raw_gen > total_baseline_kwh else 1.0

    #fixed calculations
    fixed_yearly = target_cap_kw * 1350
    fixed_itc = fixed_cap * itc_rate
    fixed_basis = fixed_cap - (fixed_itc * 0.5)
    fixed_mac = [round(fixed_basis * r * fed_tax) for r in macrs_rates]

    #tracker calculations
    tracker_yearly = target_cap_kw * (1350 * 1.25)
    tracker_itc = tracker_cap * itc_rate
    tracker_basis = tracker_cap - (tracker_itc * 0.5)
    tracker_mac = [round(tracker_basis * r * fed_tax) for r in macrs_rates]

    ann_baseline_spending = total_baseline_kwh * elec_current

    cash_flow_base = 0.0

    fixed_ann_savings = []
    tracker_ann_savings = []

    for i in range(total_yrs):
        yr_num = i + 1

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
        fixed_out_of_pocket = fixed_remaining + fixed_om - f_macrs_cred 
        
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
        tracker_out_of_pocket = tracker_remaining + tracker_om - t_macrs_cred
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
