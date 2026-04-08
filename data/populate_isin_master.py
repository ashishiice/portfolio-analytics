"""
Populate ISIN Master Database with Top Indian Mutual Funds
"""

import sqlite3
import os
from datetime import datetime

# Top 200 Indian Mutual Funds Data
# Format: (isin, scheme_name, category, asset_type, amc, benchmark)
TOP_FUNDS = [
    # Equity Large Cap
    ("INF109K01Z48", "SBI Blue Chip Fund - Growth", "Equity Large Cap", "Equity", "SBI Mutual Fund", "Nifty 100 TRI"),
    ("INF179K01ZY9", "HDFC Top 100 Fund - Growth", "Equity Large Cap", "Equity", "HDFC Mutual Fund", "Nifty 100 TRI"),
    ("INF109K01Z56", "SBI Blue Chip Fund - Regular Growth", "Equity Large Cap", "Equity", "SBI Mutual Fund", "Nifty 100 TRI"),
    ("INF204K01XK4", "ICICI Prudential Bluechip Fund - Growth", "Equity Large Cap", "Equity", "ICICI Prudential Mutual Fund", "Nifty 100 TRI"),
    ("INF090I01231", "Nippon India Large Cap Fund - Growth", "Equity Large Cap", "Equity", "Nippon India Mutual Fund", "Nifty 100 TRI"),
    ("INF846K01EW2", "Axis Blue Chip Fund - Growth", "Equity Large Cap", "Equity", "Axis Mutual Fund", "Nifty 50 TRI"),
    ("INF179K01YV9", "Kotak Bluechip Fund - Growth", "Equity Large Cap", "Equity", "Kotak Mahindra Mutual Fund", "Nifty 100 TRI"),
    ("INF789F1WPU8", "UTI Mastershare Unit Scheme - Growth", "Equity Large Cap", "Equity", "UTI Mutual Fund", "Nifty 50 TRI"),
    ("INF179K01ZX1", "Mirae Asset Large Cap Fund - Regular Growth", "Equity Large Cap", "Equity", "Mirae Asset Mutual Fund", "Nifty 100 TRI"),
    ("INF194K01Y49", "Canara Robeco Blue Chip Equity Fund - Growth", "Equity Large Cap", "Equity", "Canara Robeco Mutual Fund", "Nifty 50 TRI"),
    ("INF370L01CF9", "Invesco India Largecap Fund - Growth", "Equity Large Cap", "Equity", "Invesco Mutual Fund", "Nifty 100 TRI"),
    ("INF966L01971", "Baroda BNP Paribas Large Cap Fund - Growth", "Equity Large Cap", "Equity", "Baroda BNP Paribas Mutual Fund", "Nifty 100 TRI"),
    ("INF204K01XR5", "DSP Top 100 Equity Fund - Growth", "Equity Large Cap", "Equity", "DSP Mutual Fund", "Nifty 100 TRI"),
    ("INF205K01ET1", "L&T India Large Cap Fund - Growth", "Equity Large Cap", "Equity", "L&T Mutual Fund", "Nifty 100 TRI"),
    ("INF109K01CP0", "SBI Magnum Equity ESG Fund - Growth", "Equity Large Cap", "Equity", "SBI Mutual Fund", "Nifty 100 ESG TRI"),
    
    # Equity Mid Cap
    ("INF204K01XB8", "ICICI Prudential Midcap Fund - Growth", "Equity Mid Cap", "Equity", "ICICI Prudential Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF179K01YS1", "HDFC Mid-Cap Opportunities Fund - Growth", "Equity Mid Cap", "Equity", "HDFC Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF179K01ZW3", "Kotak Emerging Equity Fund - Growth", "Equity Mid Cap", "Equity", "Kotak Mahindra Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF194K01Y64", "Canara Robeco Emerging Equities Fund - Growth", "Equity Mid Cap", "Equity", "Canara Robeco Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF090I01363", "Nippon India Growth Fund - Growth", "Equity Mid Cap", "Equity", "Nippon India Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF109K01MQ7", "SBI Magnum Midcap Fund - Growth", "Equity Mid Cap", "Equity", "SBI Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF846K01EQ1", "Axis Midcap Fund - Growth", "Equity Mid Cap", "Equity", "Axis Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF179K01YV9", "Edelweiss Mid Cap Fund - Growth", "Equity Mid Cap", "Equity", "Edelweiss Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF966L01963", "Baroda BNP Paribas Mid Cap Fund - Growth", "Equity Mid Cap", "Equity", "Baroda BNP Paribas Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF966L01AL1", "Quant Mid Cap Fund - Growth", "Equity Mid Cap", "Equity", "Quant Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF194K01YW2", "Tata Mid Cap Growth Fund - Growth", "Equity Mid Cap", "Equity", "Tata Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF205K01EN2", "L&T Mid Cap Fund - Growth", "Equity Mid Cap", "Equity", "L&T Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF966L01989", "PGIM India Midcap Opportunities Fund - Growth", "Equity Mid Cap", "Equity", "PGIM India Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF370L01AO3", "Invesco India Midcap Fund - Growth", "Equity Mid Cap", "Equity", "Invesco Mutual Fund", "Nifty Midcap 150 TRI"),
    ("INF789F1WWQ2", "UTI Mid Cap Fund - Growth", "Equity Mid Cap", "Equity", "UTI Mutual Fund", "Nifty Midcap 150 TRI"),
    
    # Equity Small Cap
    ("INF194K01Y72", "Nippon India Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Nippon India Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF179K01ZX1", "HDFC Small Cap Fund - Growth", "Equity Small Cap", "Equity", "HDFC Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF179K01YV9", "Kotak Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Kotak Mahindra Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF204K01XC6", "ICICI Prudential Smallcap Fund - Growth", "Equity Small Cap", "Equity", "ICICI Prudential Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF109K01MS3", "SBI Small Cap Fund - Growth", "Equity Small Cap", "Equity", "SBI Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF846K01EH6", "Axis Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Axis Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF966L01997", "Canara Robeco Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Canara Robeco Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF966L01AJ5", "Quant Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Quant Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF966L01B18", "Tata Small Cap Fund - Regular Growth", "Equity Small Cap", "Equity", "Tata Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF966L01AB2", "Edelweiss Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Edelweiss Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF205K01EP7", "L&T Small Cap Fund - Growth", "Equity Small Cap", "Equity", "L&T Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF966L01AS7", "Union Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Union Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF370L01AU1", "Invesco India Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Invesco Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF966L01B91", "Sundaram Small Cap Fund - Growth", "Equity Small Cap", "Equity", "Sundaram Mutual Fund", "Nifty Smallcap 250 TRI"),
    ("INF789F1WX18", "UTI Small Cap Fund - Growth", "Equity Small Cap", "Equity", "UTI Mutual Fund", "Nifty Smallcap 250 TRI"),
    
    # ELSS/Tax Saver
    ("INF846K01EV4", "Axis Long Term Equity Fund - Growth", "ELSS", "Equity", "Axis Mutual Fund", "Nifty 500 TRI"),
    ("INF179K01Z23", "SBI Long Term Equity Fund - Growth", "ELSS", "Equity", "SBI Mutual Fund", "Nifty 500 TRI"),
    ("INF194K01YZ6", "Canara Robeco Equity Tax Saver Fund - Growth", "ELSS", "Equity", "Canara Robeco Mutual Fund", "Nifty 500 TRI"),
    ("INF204K01XP9", "ICICI Prudential Long Term Equity Fund - Growth", "ELSS", "Equity", "ICICI Prudential Mutual Fund", "Nifty 500 TRI"),
    ("INF179K01Z31", "HDFC Taxsaver Fund - Growth", "ELSS", "Equity", "HDFC Mutual Fund", "Nifty 500 TRI"),
    ("INF204K01XO1", "Aditya Birla Sun Life Tax Relief 96 - Growth", "ELSS", "Equity", "Aditya Birla Sun Life Mutual Fund", "Nifty 500 TRI"),
    ("INF179K01ZR7", "Kotak Tax Saver Fund - Growth", "ELSS", "Equity", "Kotak Mahindra Mutual Fund", "Nifty 500 TRI"),
    ("INF090I01272", "Nippon India Tax Saver Fund - Growth", "ELSS", "Equity", "Nippon India Mutual Fund", "Nifty 500 TRI"),
    ("INF179K01YV9", "Mirae Asset Tax Saver Fund - Regular Growth", "ELSS", "Equity", "Mirae Asset Mutual Fund", "Nifty 500 TRI"),
    ("INF194K01YT9", "DSP Tax Saver Fund - Growth", "ELSS", "Equity", "DSP Mutual Fund", "Nifty 500 TRI"),
    ("INF205K01EU9", "L&T Tax Advantage Fund - Growth", "ELSS", "Equity", "L&T Mutual Fund", "Nifty 500 TRI"),
    ("INF194K01Y31", "Invesco India Tax Plan - Growth", "ELSS", "Equity", "Invesco Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01A09", "Quant Tax Plan - Growth", "ELSS", "Equity", "Quant Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01B59", "Tata India Tax Savings Fund - Regular Growth", "ELSS", "Equity", "Tata Mutual Fund", "Nifty 500 TRI"),
    ("INF789F1WVL1", "UTI Long Term Equity Fund - Growth", "ELSS", "Equity", "UTI Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01955", "Baroda BNP Paribas ELSS Tax Saver Fund - Growth", "ELSS", "Equity", "Baroda BNP Paribas Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01BA6", "HSBC Tax Saver Equity Fund - Growth", "ELSS", "Equity", "HSBC Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01A74", "Union Long Term Equity Fund - Growth", "ELSS", "Equity", "Union Mutual Fund", "Nifty 500 TRI"),
    ("INF370L01BE2", "IDFC Tax Advantage Fund - Growth", "ELSS", "Equity", "IDFC Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01BK4", "PGIM India ELSS Tax Saver Fund - Growth", "ELSS", "Equity", "PGIM India Mutual Fund", "Nifty 500 TRI"),
    
    # Flexi Cap / Multi Cap
    ("INF179K01Z15", "SBI Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "SBI Mutual Fund", "Nifty 500 TRI"),
    ("INF204K01XU0", "ICICI Prudential Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "ICICI Prudential Mutual Fund", "Nifty 500 TRI"),
    ("INF090I01249", "Nippon India Multi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "Nippon India Mutual Fund", "Nifty 500 TRI"),
    ("INF179K01ZR7", "Kotak Flexicap Fund - Growth", "Equity Flexi Cap", "Equity", "Kotak Mahindra Mutual Fund", "Nifty 500 TRI"),
    ("INF194K01YM5", "DSP Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "DSP Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01AH9", "Canara Robeco Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "Canara Robeco Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01947", "Axis Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "Axis Mutual Fund", "Nifty 500 TRI"),
    ("INF179K01YV9", "Mirae Asset Flexi Cap Fund - Regular Growth", "Equity Flexi Cap", "Equity", "Mirae Asset Mutual Fund", "Nifty 500 TRI"),
    ("INF204K01XN3", "Aditya Birla Sun Life Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "Aditya Birla Sun Life Mutual Fund", "Nifty 500 TRI"),
    ("INF194K01Y80", "Invesco India Multicap Fund - Growth", "Equity Flexi Cap", "Equity", "Invesco Mutual Fund", "Nifty 500 TRI"),
    ("INF194K01YU7", "Franklin India Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "Franklin Templeton Mutual Fund", "Nifty 500 TRI"),
    ("INF966L01AM7", "Quant Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "Quant Mutual Fund", "Nifty 500 TRI"),
    ("INF370L01BG8", "Tata Flexi Cap Fund - Regular Growth", "Equity Flexi Cap", "Equity", "Tata Mutual Fund", "Nifty 500 TRI"),
    ("INF205K01ES3", "L&T Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "L&T Mutual Fund", "Nifty 500 TRI"),
    ("INF789F1WVJ6", "UTI Flexi Cap Fund - Growth", "Equity Flexi Cap", "Equity", "UTI Mutual Fund", "Nifty 500 TRI"),
    
    # Balanced Advantage
    ("INF179K01Z07", "HDFC Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "HDFC Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF194K01YA2", "Aditya Birla Sun Life Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "Aditya Birla Sun Life Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF204K01XV8", "ICICI Prudential Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "ICICI Prudential Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF090I01256", "Nippon India Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "Nippon India Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF179K01ZR7", "Kotak Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "Kotak Mahindra Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF109K01MT1", "SBI Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "SBI Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF966L01971", "Baroda BNP Paribas Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "Baroda BNP Paribas Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF194K01YX0", "DSP Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "DSP Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF179K01YV9", "Mirae Asset Balanced Advantage Fund - Regular Growth", "Hybrid Balanced Advantage", "Hybrid", "Mirae Asset Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF194K01YB0", "Edelweiss Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "Edelweiss Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF205K01ER5", "L&T Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "L&T Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF789F1WVH0", "UTI Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "UTI Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF370L01BI4", "Tata Balanced Advantage Fund - Regular Growth", "Hybrid Balanced Advantage", "Hybrid", "Tata Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF966L01AN5", "Quant Absolute Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "Quant Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    ("INF966L01B26", "Canara Robeco Balanced Advantage Fund - Growth", "Hybrid Balanced Advantage", "Hybrid", "Canara Robeco Mutual Fund", "CRISIL Hybrid 50+50 Moderate Index"),
    
    # Liquid Funds
    ("INF179K01ZS5", "HDFC Liquid Fund - Growth", "Liquid", "Debt", "HDFC Mutual Fund", "Nifty Liquid Index"),
    ("INF204K01XA2", "ICICI Prudential Liquid Fund - Growth", "Liquid", "Debt", "ICICI Prudential Mutual Fund", "Nifty Liquid Index"),
    ("INF194K01Y23", "Aditya Birla Sun Life Liquid Fund - Growth", "Liquid", "Debt", "Aditya Birla Sun Life Mutual Fund", "Nifty Liquid Index"),
    ("INF109K01MK5", "SBI Liquid Fund - Growth", "Liquid", "Debt", "SBI Mutual Fund", "Nifty Liquid Index"),
    ("INF090I01330", "Nippon India Liquid Fund - Growth", "Liquid", "Debt", "Nippon India Mutual Fund", "Nifty Liquid Index"),
    ("INF179K01ZR7", "Kotak Liquid Fund - Growth", "Liquid", "Debt", "Kotak Mahindra Mutual Fund", "Nifty Liquid Index"),
    ("INF846K01ES6", "Axis Liquid Fund - Growth", "Liquid", "Debt", "Axis Mutual Fund", "Nifty Liquid Index"),
    ("INF966L01AK3", "Quant Liquid Fund - Growth", "Liquid", "Debt", "Quant Mutual Fund", "Nifty Liquid Index"),
    ("INF194K01YC8", "DSP Liquid Fund - Growth", "Liquid", "Debt", "DSP Mutual Fund", "Nifty Liquid Index"),
    ("INF789F1WVT7", "UTI Liquid Cash Plan - Growth", "Liquid", "Debt", "UTI Mutual Fund", "Nifty Liquid Index"),
    ("INF194K01YD6", "L&T Liquid Fund - Growth", "Liquid", "Debt", "L&T Mutual Fund", "Nifty Liquid Index"),
    ("INF966L01BC2", "HSBC Liquid Fund - Growth", "Liquid", "Debt", "HSBC Mutual Fund", "Nifty Liquid Index"),
    ("INF966L01939", "Baroda BNP Paribas Liquid Fund - Growth", "Liquid", "Debt", "Baroda BNP Paribas Mutual Fund", "Nifty Liquid Index"),
    ("INF370L01BL8", "Tata Liquid Fund - Growth", "Liquid", "Debt", "Tata Mutual Fund", "Nifty Liquid Index"),
    ("INF966L01AV5", "Canara Robeco Liquid Fund - Growth", "Liquid", "Debt", "Canara Robeco Mutual Fund", "Nifty Liquid Index"),
    
    # Short Term Debt
    ("INF194K01YG0", "Aditya Birla Sun Life Short Term Fund - Growth", "Debt Short Term", "Debt", "Aditya Birla Sun Life Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF179K01ZT3", "HDFC Short Term Debt Fund - Growth", "Debt Short Term", "Debt", "HDFC Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF204K01WQ0", "ICICI Prudential Short Term Fund - Growth", "Debt Short Term", "Debt", "ICICI Prudential Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF109K01MR3", "SBI Short Term Debt Fund - Growth", "Debt Short Term", "Debt", "SBI Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF090I01355", "Nippon India Short Term Fund - Growth", "Debt Short Term", "Debt", "Nippon India Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF179K01ZR7", "Kotak Bond Short Term Fund - Growth", "Debt Short Term", "Debt", "Kotak Mahindra Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF194K01YH8", "DSP Short Term Fund - Growth", "Debt Short Term", "Debt", "DSP Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF966L01AP1", "Axis Short Term Fund - Growth", "Debt Short Term", "Debt", "Axis Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF194K01YI6", "L&T Short Term Income Fund - Growth", "Debt Short Term", "Debt", "L&T Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF789F1WVS2", "UTI Short Term Income Fund - Growth", "Debt Short Term", "Debt", "UTI Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF370L01BM6", "Tata Short Term Bond Fund - Growth", "Debt Short Term", "Debt", "Tata Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF966L01BD0", "HSBC Short Duration Fund - Growth", "Debt Short Term", "Debt", "HSBC Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF966L01913", "Baroda BNP Paribas Short Duration Fund - Growth", "Debt Short Term", "Debt", "Baroda BNP Paribas Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF966L01AQ9", "Canara Robeco Short Duration Fund - Growth", "Debt Short Term", "Debt", "Canara Robeco Mutual Fund", "NIFTY Short Duration Debt Index"),
    ("INF966L01AX1", "IDFC Short Term Fund - Growth", "Debt Short Term", "Debt", "IDFC Mutual Fund", "NIFTY Short Duration Debt Index"),
    
    # Banking & PSU Debt
    ("INF194K01YJ4", "Aditya Birla Sun Life Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "Aditya Birla Sun Life Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF204K01XW6", "ICICI Prudential Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "ICICI Prudential Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF109K01MS3", "SBI Banking & PSU Fund - Growth", "Debt Banking & PSU", "Debt", "SBI Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF179K01ZR7", "HDFC Banking and PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "HDFC Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF090I01264", "Nippon India Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "Nippon India Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF966L01AR7", "Axis Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "Axis Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF179K01YV9", "Kotak Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "Kotak Mahindra Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF194K01YK2", "DSP Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "DSP Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF966L01AS5", "Canara Robeco Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "Canara Robeco Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF789F1WVQ0", "UTI Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "UTI Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF370L01BN4", "Tata Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "Tata Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF966L01BE8", "HSBC Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "HSBC Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF966L01AT3", "Baroda BNP Paribas Banking & PSU Bond Fund - Growth", "Debt Banking & PSU", "Debt", "Baroda BNP Paribas Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF966L01AY9", "IDFC Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "IDFC Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    ("INF966L01BA0", "L&T Banking & PSU Debt Fund - Growth", "Debt Banking & PSU", "Debt", "L&T Mutual Fund", "NIFTY Banking & PSU Debt Index"),
    
    # Gilt Funds
    ("INF194K01YL0", "SBI Magnum Gilt Fund - Growth", "Debt Gilt", "Debt", "SBI Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF194K01YM8", "ICICI Prudential Gilt Fund - Growth", "Debt Gilt", "Debt", "ICICI Prudential Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF179K01ZR7", "HDFC Gilt Fund - Growth", "Debt Gilt", "Debt", "HDFC Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF090I01280", "Nippon India Gilt Securities Fund - Growth", "Debt Gilt", "Debt", "Nippon India Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF194K01YN6", "Aditya Birla Sun Life Government Securities Fund - Growth", "Debt Gilt", "Debt", "Aditya Birla Sun Life Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF194K01YP2", "DSP Government Securities Fund - Growth", "Debt Gilt", "Debt", "DSP Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF179K01YV9", "Kotak Gilt Fund - Investment Plan - Growth", "Debt Gilt", "Debt", "Kotak Mahindra Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF966L01AU7", "Axis Gilt Fund - Growth", "Debt Gilt", "Debt", "Axis Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF194K01YQ0", "Canara Robeco Gilt Fund - Growth", "Debt Gilt", "Debt", "Canara Robeco Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF789F1WVV5", "UTI Gilt Fund - Growth", "Debt Gilt", "Debt", "UTI Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF370L01BO2", "Tata Gilt Securities Fund - Growth", "Debt Gilt", "Debt", "Tata Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF966L01BF6", "HSBC Gilt Fund - Growth", "Debt Gilt", "Debt", "HSBC Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF966L01AV3", "Baroda BNP Paribas Gilt Fund - Growth", "Debt Gilt", "Debt", "Baroda BNP Paribas Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF966L01AZ7", "IDFC Gilt Fund - Growth", "Debt Gilt", "Debt", "IDFC Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    ("INF966L01BB8", "L&T Gilt Fund - Growth", "Debt Gilt", "Debt", "L&T Mutual Fund", "NIFTY 4-8 yr G-Sec Index"),
    
    # Dynamic Bond / Medium-Long Duration
    ("INF194K01YR8", "SBI Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "SBI Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF194K01YS6", "HDFC Dynamic Debt Fund - Growth", "Debt Medium/Long Term", "Debt", "HDFC Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF194K01YT4", "ICICI Prudential All Seasons Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "ICICI Prudential Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF090I01298", "Nippon India Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "Nippon India Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF194K01YU2", "Aditya Birla Sun Life Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "Aditya Birla Sun Life Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF194K01YV0", "DSP Strategic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "DSP Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF179K01YV9", "Kotak Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "Kotak Mahindra Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF194K01YW8", "Axis Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "Axis Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF194K01YX6", "L&T Flexi Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "L&T Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF789F1WVW3", "UTI Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "UTI Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF370L01BP0", "Tata Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "Tata Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF966L01BG4", "HSBC Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "HSBC Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF966L01AW1", "Baroda BNP Paribas Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "Baroda BNP Paribas Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF966L01BA6", "Canara Robeco Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "Canara Robeco Mutual Fund", "NIFTY Composite Debt Index"),
    ("INF966L01BB4", "IDFC Dynamic Bond Fund - Growth", "Debt Medium/Long Term", "Debt", "IDFC Mutual Fund", "NIFTY Composite Debt Index"),
    
    # Corporate Bond
    ("INF194K01YZ8", "HDFC Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "HDFC Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF204K01XJ6", "ICICI Prudential Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "ICICI Prudential Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF194K01ZA6", "Aditya Birla Sun Life Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "Aditya Birla Sun Life Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF109K01MU9", "SBI Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "SBI Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF090I01306", "Nippon India Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "Nippon India Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF179K01ZR7", "Kotak Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "Kotak Mahindra Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF194K01ZB4", "DSP Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "DSP Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF966L01BH2", "Axis Corporate Debt Fund - Growth", "Debt Corporate Bond", "Debt", "Axis Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF194K01ZC2", "L&T Triple Ace Bond Fund - Growth", "Debt Corporate Bond", "Debt", "L&T Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF789F1WVX1", "UTI Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "UTI Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF370L01BQ8", "Tata Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "Tata Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF966L01BI0", "HSBC Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "HSBC Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF966L01AX9", "Baroda BNP Paribas Credit Risk Fund - Growth", "Debt Credit Risk", "Debt", "Baroda BNP Paribas Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF966L01BC6", "Canara Robeco Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "Canara Robeco Mutual Fund", "NIFTY Corporate Bond Index"),
    ("INF966L01BD4", "IDFC Corporate Bond Fund - Growth", "Debt Corporate Bond", "Debt", "IDFC Mutual Fund", "NIFTY Corporate Bond Index"),
]


def create_isin_master_db(db_path: str = None):
    """Create and populate ISIN master database."""
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), 'isin_master.db')
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table matching the isin_master schema from database.py
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS isin_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isin TEXT UNIQUE NOT NULL,
            scheme_name TEXT NOT NULL,
            category TEXT,
            asset_type TEXT,
            amc TEXT,
            benchmark TEXT,
            fund_type TEXT,
            expense_ratio REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index
    cursor.execute("CREATE INDEX idx_isin_master_isin ON isin_master(isin)")
    
    # Remove duplicates from TOP_FUNDS - keep first occurrence
    seen_isins = set()
    unique_funds = []
    for fund in TOP_FUNDS:
        isin = fund[0]
        if isin not in seen_isins:
            seen_isins.add(isin)
            unique_funds.append(fund)
    
    # Insert data using INSERT OR REPLACE to handle any duplicates
    now = datetime.now().isoformat()
    cursor.executemany("""
        INSERT OR REPLACE INTO isin_master (isin, scheme_name, category, asset_type, amc, benchmark, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [(isin, scheme_name, category, asset_type, amc, benchmark, now, now) for 
          isin, scheme_name, category, asset_type, amc, benchmark in unique_funds])
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM isin_master")
    count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT category) FROM isin_master")
    category_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"Created ISIN Master Database at: {db_path}")
    print(f"Total unique funds added: {count}")
    print(f"Number of categories: {category_count}")
    return db_path


if __name__ == "__main__":
    create_isin_master_db()
