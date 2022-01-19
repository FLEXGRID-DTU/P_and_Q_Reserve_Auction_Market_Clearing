# -*- coding: utf-8 -*-
"""
Created on Thu Sep 30 15:12:44 2021

@author: rahul
"""
import numpy as np
import pandas as pd
import pyomo.kernel as pyo


def addRow_withIndex(df,ls,ID):
    """
    Given a dataframe and a list, append the list as a new row to the dataframe.

    :param df: <DataFrame> The original dataframe
    :param ls: <list> The new row to be added
    :param ID: <str> Index for the new row
    :return: <DataFrame> The dataframe with the newly appended row
    """
    numEl = len(ls)
    newRow = pd.DataFrame(np.array(ls).reshape(1,numEl), columns = list(df.columns), index=[ID])
    df = df.append(newRow)
    df.index.name='ID'
    return df

def Market_clearing(Bid, Setpoint_P, Setpoint_Q, orderbook_request, orderbook_offer, accepted_requests, accepted_offers,  nodes, NetworkData, SocialWelfare, ProcurementCost):
    
    matches = pd.DataFrame(columns = ['Offer','Offer Bus','Request','Request Bus','P_or_Q','Direction','Quantity','Matching Price','Time_target'])   
    
    # Seperating Offers and Requests 
    offers_P =Bid[(Bid.Bid == 'Offer') & (Bid.P_or_Q == 'P')]
    requests_P= Bid[(Bid.Bid == 'Request') &( Bid.P_or_Q == 'P')]
    
    offers_Q =Bid[(Bid.Bid == 'Offer') & (Bid.P_or_Q == 'Q')]
    requests_Q = Bid[(Bid.Bid == 'Request') & (Bid.P_or_Q == 'Q')]
    
    #Extracting system data data
    baseMVA = NetworkData['base_MVA']
    node_data = NetworkData['bus_data']
    branch_data = NetworkData['branch_data']
    
    
    model = pyo.block()
    model.dual = pyo.suffix(direction=pyo.suffix.IMPORT)

    # Defining Parameters 
    model.N = nodes # nodes
    model.B = [(branch_data.loc[i, 'From'], branch_data.loc[i, 'To'])
                                            for i in branch_data.index]  # lines
    
    # Node Voltage limits
    model.Vmin_sq = pyo.parameter_dict()
    for i in node_data.index:
        model.Vmin_sq[i] = pyo.parameter(node_data.loc[i, 'Vmin'] ** 2)
    model.Vmax_sq = pyo.parameter_dict()
    for i in node_data.index:
        model.Vmax_sq[i] = pyo.parameter(node_data.loc[i, 'Vmax'] ** 2)
    
    # Lines Data
    model.R = pyo.parameter_dict()
    for i in branch_data.index:
        model.R[branch_data.loc[i, 'From'], branch_data.loc[i, 'To']] = pyo.parameter(branch_data.loc[i, 'R'])
    model.X = pyo.parameter_dict()
    for i in branch_data.index:
        model.X[branch_data.loc[i, 'From'], branch_data.loc[i, 'To']] = pyo.parameter(branch_data.loc[i, 'X'])

    # SetPoints
    model.P_init = pyo.parameter_dict()
    bus=0
    for i in node_data.index:
        model.P_init[i] = pyo.parameter(Setpoint_P[bus] /baseMVA)
        bus+=1
        
    model.Q_init = pyo.parameter_dict()
    bus=0
    for i in node_data.index:
        model.Q_init[i] = pyo.parameter(Setpoint_Q[bus] /baseMVA)
        bus+=1
          
    # Offers
    model.off_P_max = pyo.parameter_dict()
    model.O_P = offers_P.index.tolist()
    for o in model.O_P:
        model.off_P_max[o] = pyo.parameter(offers_P.loc[o, 'Quantity'] /baseMVA)
        
    model.off_Q_max = pyo.parameter_dict()
    model.O_Q = offers_Q.index.tolist()
    for o in model.O_Q:
        model.off_Q_max[o] = pyo.parameter(offers_Q.loc[o, 'Quantity'] /baseMVA)

    # Requests
    model.Req_P_max = pyo.parameter_dict()
    model.R_P = requests_P.index.tolist()
    for o in model.R_P:
        model.Req_P_max[o] = pyo.parameter(requests_P.loc[o, 'Quantity'] /baseMVA)
        
    model.Req_Q_max = pyo.parameter_dict()
    model.R_Q = requests_Q.index.tolist()
    for o in model.R_Q:
        model.Req_Q_max[o] = pyo.parameter(requests_Q.loc[o, 'Quantity'] /baseMVA)       

    #%% Variables
    
    # Voltage square
    model.V_sq = pyo.variable_dict()
    for i in model.N:
        model.V_sq[i] = pyo.variable(lb=node_data.loc[i, 'Vmin'] ** 2, ub=node_data.loc[i, 'Vmax']** 2,value=1)

    # Line flow
    
    # S max is defined as a variable to use it in conic constraint 
    model.Smax = pyo.variable_dict()
    for i in branch_data.index:
        model.Smax[branch_data.loc[i, 'From'], branch_data.loc[i, 'To']] = pyo.variable(lb=branch_data.loc[i, 'Lim']/baseMVA, ub=branch_data.loc[i, 'Lim']/baseMVA)
       
    model.P_lin = pyo.variable_dict()
    for i,j in model.B:
        model.P_lin[i,j] = pyo.variable( value=0)
    
    model.Q_lin = pyo.variable_dict()
    for i,j in model.B:
        model.Q_lin[i,j] = pyo.variable(value=0)
    
    # Accepted_offers          
    model.off_P = pyo.variable_dict()
    for o in model.O_P:
        model.off_P[o] = pyo.variable(lb=0, ub=model.off_P_max[o], value=0)

    model.off_Q = pyo.variable_dict()
    for o in model.O_Q:
        model.off_Q[o] = pyo.variable(lb=0, ub=model.off_Q_max[o], value=0)   
    
    #Accepted Requests
    model.Req_P = pyo.variable_dict()
    for o in model.R_P:
        model.Req_P[o] = pyo.variable(lb=0, ub=model.Req_P_max[o], value=0)

    model.Req_Q = pyo.variable_dict()
    for o in model.R_Q:
        model.Req_Q[o] =pyo.variable(lb=0, ub=model.Req_Q_max[o], value=0)
        
    # Change in node power injection
    model.P_del = pyo.variable_dict()
    for i in model.N:
        model.P_del[i] = pyo.variable(value=0)    
    
    model.Q_del = pyo.variable_dict()
    for i in model.N:
        model.Q_del[i] = pyo.variable(value=0)  
         
    #%% Constraints
    # Active and reactive powerflows equations
    model.active_power_flow = pyo.constraint_dict()
    for k in model.N:
        Lhs = sum(model.P_lin[j, i] for j, i in model.B if i == k) - sum(model.P_lin[i, j] for i, j in model.B if i == k) +\
            model.P_init[k] + model.P_del[k]
        model.active_power_flow[k] = pyo.constraint(body=Lhs,rhs=0)
        
    model.reactive_power_flow = pyo.constraint_dict()
    for k in model.N:
        Lhs = sum(model.Q_lin[j, i] for j, i in model.B if i == k) - sum(model.Q_lin[i, j] for i, j in model.B if i == k) +\
            (model.Q_init[k] + model.Q_del[k])
        model.reactive_power_flow[k] = pyo.constraint(body=Lhs,rhs=0)
    
    # Line flow limit
    model.Lin_lim = pyo.constraint_dict()
    for i,j in model.B:
        x = [model.P_lin[i,j],model.Q_lin[i,j]]
        model.Lin_lim[i,j] = pyo.conic.quadratic(model.Smax[i,j], x)
    
    #Voltage Drop
    model.voltage_drop = pyo.constraint_dict()
    for i,j in model.B:
        Lhs = model.V_sq[j]
        Rhs = model.V_sq[i] - 2 * (model.R[i, j] * model.P_lin[i, j] + model.X[i, j] * model.Q_lin[i, j])
        model.voltage_drop[i,j] = pyo.constraint(body=Lhs-Rhs,rhs=0)
    
    # Link between offers and Requests to their respective nodes
    model.P_del_cal = pyo.constraint_dict()
    for i in model.N:
        sum_off_req_p = 0
        for o in model.O_P:
            if (Bid.loc[o,'Bus']==i) and (Bid.loc[o,'Direction']=='Up'):
                sum_off_req_p+=model.off_P[o]
            elif (Bid.loc[o,'Bus']==i) and (Bid.loc[o,'Direction']=='Down'):
                sum_off_req_p-=model.off_P[o]
        for o in model.R_P:
            if (Bid.loc[o,'Bus']==i) and (Bid.loc[o,'Direction']=='Up'):
                sum_off_req_p-=model.Req_P[o]
            elif (Bid.loc[o,'Bus']==i) and (Bid.loc[o,'Direction']=='Down'):
                sum_off_req_p+=model.Req_P[o]
        model.P_del_cal[i] = pyo.constraint(body=model.P_del[i]-sum_off_req_p, rhs=0)    
        
    model.Q_del_cal = pyo.constraint_dict()
    for i in model.N:
        sum_off_req_q = 0
        for o in model.O_Q:
            if (Bid.loc[o,'Bus']==i) and (Bid.loc[o,'Direction']=='Up'):
                sum_off_req_q+=model.off_Q[o]
            elif (Bid.loc[o,'Bus']==i) and (Bid.loc[o,'Direction']=='Down'):
                sum_off_req_q-=model.off_Q[o]
        for o in model.R_Q:
            if (Bid.loc[o,'Bus']==i) and (Bid.loc[o,'Direction']=='Up'):
                sum_off_req_q-=model.Req_Q[o]
            elif (Bid.loc[o,'Bus']==i) and (Bid.loc[o,'Direction']=='Down'):
                sum_off_req_q+=model.Req_Q[o]                
        model.Q_del_cal[i] = pyo.constraint(body=model.Q_del[i]-sum_off_req_q, rhs=0)

    # Constraint to match sum of offers with request           
    sum_off_p=0
    sum_req_p=0
    for o in model.O_P:
        sum_off_p+=model.off_P[o]
    for o in model.R_P:
        sum_req_p+=model.Req_P[o]
    model.off_Req_Cor_P =  pyo.constraint(body=sum_req_p-sum_off_p, rhs=0)  
    
    sum_off_q=0
    sum_req_q=0
    for o in model.O_Q:
        sum_off_q+=model.off_Q[o]
    for o in model.R_Q:
        sum_req_q+=model.Req_Q[o]
    model.off_Req_Cor_Q =  pyo.constraint(body=sum_off_q-sum_req_q, rhs=0)      
    #%% Objective function
    
    model.min_costs = pyo.objective(-baseMVA * (sum(model.Req_P[o]*Bid.loc[o,'Price'] for o in model.R_P) +\
                                               sum(model.Req_Q[o]*Bid.loc[o,'Price'] for o in model.R_Q) -\
                                               sum(model.off_P[o]*Bid.loc[o,'Price'] for o in model.O_P) -\
                                               sum(model.off_Q[o]*Bid.loc[o,'Price'] for o in model.O_Q) ))

    #%% Specify solver settings and solve model
    solver = pyo.SolverFactory('mosek')
    
    display_results =False
    if display_results == True:
        solver.solve(model, tee=True)
    else:
        solver.solve(model)    
    #%% Collecting Required Outputs

    # Collecting accepted_requests and orderbook_request  
    for o in model.R_P:
        if (model.Req_P[o].value*baseMVA >0):
            ac_req=[requests_P.loc[o, 'Bus'], requests_P.loc[o, 'Direction'],requests_P.loc[o, 'P_or_Q'], round(model.Req_P[o].value*baseMVA, 4), requests_P.loc[o, 'Time_target']]
            accepted_requests= addRow_withIndex(accepted_requests,ac_req,o)
        req_rem=round(requests_P.loc[o, 'Quantity'] - model.Req_P[o].value*baseMVA,3) 
        if (req_rem > 0):
            new=requests_P.loc[o,:]
            new['Quantity']=req_rem
            orderbook_request= orderbook_request.append(new)
    for o in model.R_Q:
        if (model.Req_Q[o].value*baseMVA >0):
            ac_req=[requests_Q.loc[o, 'Bus'], requests_Q.loc[o, 'Direction'],requests_Q.loc[o, 'P_or_Q'], round(model.Req_Q[o].value*baseMVA, 4), requests_Q.loc[o, 'Time_target']]
            accepted_requests= addRow_withIndex(accepted_requests,ac_req,o)
        req_rem=round(requests_Q.loc[o, 'Quantity'] - model.Req_Q[o].value*baseMVA,3) 
        if (req_rem > 0):
            new=requests_Q.loc[o,:]
            new['Quantity']=req_rem
            orderbook_request= orderbook_request.append(new)

    # Collecting accepted_offer and orderbook_offer
    for o in model.O_P:
        if (model.off_P[o].value*baseMVA >0):
            ac_off=[offers_P.loc[o, 'Bus'], offers_P.loc[o, 'Direction'],offers_P.loc[o, 'P_or_Q'], round(model.off_P[o].value*baseMVA, 4), offers_P.loc[o, 'Time_target']]
            accepted_offers= addRow_withIndex(accepted_offers,ac_off,o)
        off_rem=round(offers_P.loc[o, 'Quantity'] - model.off_P[o].value*baseMVA,3) 
        if (off_rem > 0):
            new=offers_P.loc[o,:]
            new['Quantity']=off_rem
            orderbook_offer= orderbook_offer.append(new)      
    for o in model.O_Q:
        if (model.off_Q[o].value*baseMVA >0):
            ac_off=[offers_Q.loc[o, 'Bus'], offers_Q.loc[o, 'Direction'],offers_Q.loc[o, 'P_or_Q'], round(model.off_Q[o].value*baseMVA, 4), offers_Q.loc[o, 'Time_target']]
            accepted_offers= addRow_withIndex(accepted_offers,ac_off,o)
        off_rem=round(offers_Q.loc[o, 'Quantity'] - model.off_Q[o].value*baseMVA,3) 
        if (off_rem > 0):
            new=offers_Q.loc[o,:]
            new['Quantity']=off_rem
            orderbook_offer= orderbook_offer.append(new) 
        
    # Updating SocialWelfare and ProcurementCost
    SocialWelfare+= pyo.value(-model.min_costs)
    ProcurementCost += sum(model.off_P[o].value*Bid.loc[o,'Price'] for o in model.O_P) +\
                        sum(model.off_Q[o].value*Bid.loc[o,'Price'] for o in model.O_Q)
    
    return matches, orderbook_request, orderbook_offer, accepted_requests, accepted_offers, SocialWelfare, ProcurementCost