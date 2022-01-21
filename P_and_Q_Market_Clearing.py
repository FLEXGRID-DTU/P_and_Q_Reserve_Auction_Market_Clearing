# -*- coding: utf-8 -*-
"""
Created on Thu Sep 30 14:08:38 2021

@author: rnelli
"""

import pandas as pd
import ast
from Market_clearing import Market_clearing
#%% Case data

# Readin Real and Reactive power setpoints
Setpoint_P = pd.read_csv('Data_Files\Setpoint_P.csv',index_col='Time_target',converters={1:ast.literal_eval}) # Baseline injections at each node (negative for retrieval)
Setpoint_Q  = pd.read_csv('Data_Files\Setpoint_Q.csv',index_col='Time_target',converters={1:ast.literal_eval})

# Loading Network Data
NetworkData = {}
NetworkData['base_MVA'] = pd.read_excel(open('Data_Files/network15bus.xlsx', 'rb'),sheet_name='baseMVA',index_col=False)['baseMVA'].to_list()[0]
NetworkData['bus_data'] = pd.read_excel(open('Data_Files/network15bus.xlsx', 'rb'),sheet_name='Bus',index_col=0)
NetworkData['bus_data'].columns = ['type', 'Vmax', 'Vmin']
NetworkData['bus_data'].index.names = ['Bus']
NetworkData['branch_data'] = pd.read_excel(open('Data_Files/network15bus.xlsx', 'rb'),sheet_name='Branch',index_col=0) 
NetworkData['branch_data'].columns = ['From','To','R','X','Lim']
NetworkData['branch_data'].index.names = ['Line']
# NetworkData['Gen_data'] = pd.read_excel(open('Data_Files/network15bus.xlsx', 'rb'),sheet_name='Gen',index_col=0) 

# Node Indexes
nodes = list(NetworkData['bus_data'].index)

# Bid data
all_bids = pd.read_csv('Data_Files\Bids.csv',index_col=0)

all_bids.columns = ['Bid','Type','Bus','P_or_Q', 'Direction','Quantity','Price','Time_target','Time_stamp']
all_bids.index.names = ['ID']


# Create empty dataframes to contain the bids that were not matched (order book)
orderbook_offer = pd.DataFrame(columns = ['ID','Bus','P_or_Q','Direction','Quantity','Price','Time_target','Time_stamp'])
orderbook_offer.set_index('ID',inplace=True)
orderbook_request = pd.DataFrame(columns = ['ID','Bus','Type','P_or_Q','Direction','Quantity','Price','Time_target','Time_stamp'])
orderbook_request.set_index('ID',inplace=True)

# Create an empty dataframe to contain the accepted requests and offers
accepted_requests = pd.DataFrame(columns = ['ID','Bus','Direction','P_or_Q','Dispatch Change','Time_target'])
accepted_requests.set_index('ID',inplace=True)
accepted_offers = pd.DataFrame(columns = ['ID','Bus','Direction','P_or_Q','Dispatch Change','Time_target'])
accepted_offers.set_index('ID',inplace=True)

# initial data
SocialWelfare=0
ProcurementCost=0
for t in Setpoint_P.index:
    Bid_t=all_bids[all_bids.Time_target == t]
    #%% Fuction for auction market clearing
    orderbook_request, orderbook_offer, accepted_requests, accepted_offers, SocialWelfare, ProcurementCost = Market_clearing(Bid_t, Setpoint_P.at[t,'Setpoint_P'], Setpoint_Q.at[t,'Setpoint_Q'] , orderbook_request, orderbook_offer, accepted_requests, accepted_offers, nodes, NetworkData, SocialWelfare, ProcurementCost)        


orderbook_offer.columns = ['location','type', 'regulation','volume','price','timetarget','timestamp']
orderbook_offer.index.names = ['offerId']
orderbook_request.columns = ['location','requestType','type', 'regulation','volume','price','timetarget','timestamp']
orderbook_request.index.names = ['flexRequestId']

accepted_offers.columns = ['location', 'regulation','type','volume','timetarget']
accepted_offers.index.names = ['offerId']
accepted_requests.columns = ['location', 'regulation','type','volume','timetarget']
accepted_requests.index.names = ['flexRequestId']
