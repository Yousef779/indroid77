import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, 
                             QGroupBox, QScrollArea, QFormLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTabWidget, QListWidget,
                             QCheckBox, QDoubleSpinBox, QSpinBox)
from PyQt5.QtCore import QTimer, Qt
from binance.um_futures import UMFutures
import ta
import pandas as pd
from time import sleep
from binance.error import ClientError
import threading
from datetime import datetime
# ⚠️ تحذير: هذه الطريقة غير آمنة ولا ينصح بها للتطبيقات النهائية
api = "xRmCkC9s8LEL4Yujp5CHVaPcgSYoie0vHLWEsBspLYNTiioKSrEorrV3iqnrqerZ"
secret = "Uz5cdxd1IedTDwJB0teMZqP0k1sxUdr67GyETM8Y7Qd3UfK9VJm38Y2hipUKT7GY"

class TradingBotGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # تعريف العميل كمتغير داخل الكلاس
        self.client = UMFutures(key=api, secret=secret)
        
        self.setWindowTitle("بوت تداول Binance للمضاربة السريعة")
        self.setGeometry(100, 100, 1200, 800)
        self.running = False
        self.current_settings = {
            'tp': 0.012,  # 1.2%
            'sl': 0.009,  # 0.9%
            'volume': 10,
            'leverage': 50,
            'margin_type': 'ISOLATED',
            'max_positions': 5,
            'timeframe': '5m',
            'strategy': 'EMA + RSI + Volume (الزخم السريع)'
        }
        
        self.strategy_settings = {
            'EMA + RSI + Volume (الزخم السريع)': {
                'ema_fast': 9,
                'ema_slow': 21,
                'rsi_length': 6,
                'rsi_overbought': 70,
                'rsi_oversold': 30
            },
            'Bollinger Bands + Stochastic (اختناق ثم انفجار)': {
                'bb_length': 20,
                'bb_std': 2,
                'stoch_length': 14,
                'stoch_overbought': 80,
                'stoch_oversold': 20
            },
            'VWAP + OBV (تأكيد الحجم)': {
                'vwap_length': 20,
                'obv_ema': 21
            },
            'EMA Cross Scalping (تقاطع المتوسطات السريع)': {
                'ema_very_fast': 5,
                'ema_fast': 9,
                'ema_slow': 21,
                'volume_threshold': 1.5
            },
            'Price Action Scalping (حركة السعر السريعة)': {
                'pinbar_threshold': 0.6,
                'inside_bar_ratio': 0.9,
                'min_body_size': 0.0005
            },
            'Order Flow Scalping (تدفق الأوامر)': {
                'obv_threshold': 10000,
                'vwap_distance': 0.0015,
                'volume_spike': 2.0
            },
            'Liquidity Grab (السيولة السريعة)': {
                'wick_ratio': 0.7,
                'retracement_depth': 0.382,
                'volume_confirmation': 1.8
            },
            'Fibonacci Momentum (زخم فيبوناتشي)': {
                'fib_level': 0.618,
                'rsi_confirm': 55,
                'macd_signal': 0.001
            }
        }
        
        # إعدادات الأزواج الجديدة
        self.all_symbols = []
        self.selected_symbols = []
        self.trading_mode = "SELECTED"  # ALL أو SELECTED
        
        self.init_ui()
        self.update_balance()
        self.update_open_positions()
        self.update_open_orders()
        QTimer.singleShot(1000, self.load_all_symbols)
    
    def init_ui(self):
        # إنشاء الويدجت الرئيسي
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # التخطيط الرئيسي
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        
        # إنشاء تبويبات
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # تبويب التحكم الرئيسي
        control_tab = QWidget()
        tab_widget.addTab(control_tab, "التحكم")
        
        # تبويب التحليلات
        analysis_tab = QWidget()
        tab_widget.addTab(analysis_tab, "التحليلات")
        
        # تبويب الصفقات
        trades_tab = QWidget()
        tab_widget.addTab(trades_tab, "الصفقات")
        
        # تبويب الأوامر
        orders_tab = QWidget()
        tab_widget.addTab(orders_tab, "الأوامر")
        
        # تبويب إدارة الأزواج
        symbols_tab = QWidget()
        tab_widget.addTab(symbols_tab, "إدارة الأزواج")
        
        # تبويب إدارة الاستراتيجيات الجديد
        strategies_tab = QWidget()
        tab_widget.addTab(strategies_tab, "إدارة الاستراتيجيات")
        
        # --------------------------
        # محتوى تبويب التحكم
        # --------------------------
        control_layout = QVBoxLayout()
        control_tab.setLayout(control_layout)
        
        # لوحة المعلومات
        info_group = QGroupBox("معلومات الحساب")
        control_layout.addWidget(info_group)
        
        info_layout = QFormLayout()
        info_group.setLayout(info_layout)
        
        self.balance_label = QLabel("جاري التحميل...")
        info_layout.addRow("الرصيد:", self.balance_label)
        
        self.positions_label = QLabel("0")
        info_layout.addRow("الصفقات المفتوحة:", self.positions_label)
        
        self.orders_label = QLabel("0")
        info_layout.addRow("الأوامر النشطة:", self.orders_label)
        
        self.status_label = QLabel("متوقف")
        info_layout.addRow("حالة البوت:", self.status_label)
        
        # لوحة الإعدادات
        settings_group = QGroupBox("إعدادات التداول")
        control_layout.addWidget(settings_group)
        
        settings_layout = QFormLayout()
        settings_group.setLayout(settings_layout)
        
        self.tp_entry = QLineEdit(str(self.current_settings['tp'] * 100))
        settings_layout.addRow("وقف الربح (%):", self.tp_entry)
        
        self.sl_entry = QLineEdit(str(self.current_settings['sl'] * 100))
        settings_layout.addRow("وقف الخسارة (%):", self.sl_entry)
        
        self.volume_entry = QLineEdit(str(self.current_settings['volume']))
        settings_layout.addRow("حجم الصفقة:", self.volume_entry)
        
        self.leverage_entry = QLineEdit(str(self.current_settings['leverage']))
        settings_layout.addRow("الرافعة المالية:", self.leverage_entry)
        
        self.margin_type_combobox = QComboBox()
        self.margin_type_combobox.addItems(['ISOLATED', 'CROSS'])
        self.margin_type_combobox.setCurrentText(self.current_settings['margin_type'])
        settings_layout.addRow("نوع الهامش:", self.margin_type_combobox)
        
        self.max_positions_entry = QLineEdit(str(self.current_settings['max_positions']))
        settings_layout.addRow("الحد الأقصى للصفقات:", self.max_positions_entry)
        
        # لوحة الاستراتيجية
        strategy_group = QGroupBox("إعدادات الاستراتيجية")
        control_layout.addWidget(strategy_group)
        
        strategy_layout = QFormLayout()
        strategy_group.setLayout(strategy_layout)
        
        self.strategy_combobox = QComboBox()
        self.strategy_combobox.addItems(list(self.strategy_settings.keys()))
        self.strategy_combobox.setCurrentText(self.current_settings['strategy'])
        strategy_layout.addRow("الاستراتيجية:", self.strategy_combobox)
        
        self.timeframe_combobox = QComboBox()
        self.timeframe_combobox.addItems(['1m', '3m', '5m', '15m', '30m'])
        self.timeframe_combobox.setCurrentText(self.current_settings['timeframe'])
        strategy_layout.addRow("الإطار الزمني:", self.timeframe_combobox)
        
        # لوحة التحكم
        control_group = QGroupBox("التحكم")
        control_layout.addWidget(control_group)
        
        control_layout_btns = QHBoxLayout()
        control_group.setLayout(control_layout_btns)
        
        self.start_btn = QPushButton("بدء البوت")
        self.start_btn.clicked.connect(self.start_bot)
        control_layout_btns.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("إيقاف البوت")
        self.stop_btn.clicked.connect(self.stop_bot)
        self.stop_btn.setEnabled(False)
        control_layout_btns.addWidget(self.stop_btn)
        
        # لوحة السجل
        log_group = QGroupBox("سجل الأحداث")
        control_layout.addWidget(log_group)
        
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # --------------------------
        # محتوى تبويب التحليلات
        # --------------------------
        analysis_layout = QVBoxLayout()
        analysis_tab.setLayout(analysis_layout)
        
        self.analysis_table = QTableWidget()
        self.analysis_table.setColumnCount(8)
        self.analysis_table.setHorizontalHeaderLabels([
            "الزوج", "الاستراتيجية", "السعر", "الإشارة", 
            "المؤشر 1", "المؤشر 2", "المؤشر 3", "الوقت"
        ])
        self.analysis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        analysis_layout.addWidget(self.analysis_table)
        
        # --------------------------
        # محتوى تبويب الصفقات
        # --------------------------
        trades_layout = QVBoxLayout()
        trades_tab.setLayout(trades_layout)
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(7)
        self.positions_table.setHorizontalHeaderLabels([
            "الزوج", "الجانب", "الحجم", "سعر الدخول", 
            "الربح الحالي", "الوقف", "الوقت"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        trades_layout.addWidget(self.positions_table)
        
        # --------------------------
        # محتوى تبويب الأوامر
        # --------------------------
        orders_layout = QVBoxLayout()
        orders_tab.setLayout(orders_layout)
        
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(6)
        self.orders_table.setHorizontalHeaderLabels([
            "الزوج", "النوع", "الحجم", "السعر", 
            "الوقف/الربح", "الوقت"
        ])
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        orders_layout.addWidget(self.orders_table)
        
        # --------------------------
        # محتوى تبويب إدارة الأزواج
        # --------------------------
        symbols_layout = QVBoxLayout()
        symbols_tab.setLayout(symbols_layout)
        
        # مجموعة تصفية الأزواج
        filter_group = QGroupBox("تصفية الأزواج")
        symbols_layout.addWidget(filter_group)
        
        filter_layout = QHBoxLayout()
        filter_group.setLayout(filter_layout)
        
        self.symbol_filter = QLineEdit()
        self.symbol_filter.setPlaceholderText("ابحث عن زوج...")
        self.symbol_filter.textChanged.connect(self.filter_symbols)
        filter_layout.addWidget(self.symbol_filter)
        
        self.refresh_symbols_btn = QPushButton("تحديث القائمة")
        self.refresh_symbols_btn.clicked.connect(self.load_all_symbols)
        filter_layout.addWidget(self.refresh_symbols_btn)
        
        # مجموعة اختيار الأزواج
        symbols_group = QGroupBox("الأزواج المتاحة")
        symbols_layout.addWidget(symbols_group)
        
        symbols_group_layout = QHBoxLayout()
        symbols_group.setLayout(symbols_group_layout)
        
        # قائمة جميع الأزواج
        self.all_symbols_list = QListWidget()
        self.all_symbols_list.setSelectionMode(QListWidget.MultiSelection)
        symbols_group_layout.addWidget(self.all_symbols_list)
        
        # أزرار التحكم
        buttons_layout = QVBoxLayout()
        symbols_group_layout.addLayout(buttons_layout)
        
        self.select_all_btn = QPushButton("اختيار الكل")
        self.select_all_btn.clicked.connect(self.select_all_symbols)
        buttons_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("إلغاء الكل")
        self.deselect_all_btn.clicked.connect(self.deselect_all_symbols)
        buttons_layout.addWidget(self.deselect_all_btn)
        
        self.save_symbols_btn = QPushButton("حفظ الأزواج المختارة")
        self.save_symbols_btn.clicked.connect(self.save_selected_symbols)
        buttons_layout.addWidget(self.save_symbols_btn)
        
        # قائمة الأزواج المختارة
        selected_group = QGroupBox("الأزواج المختارة")
        symbols_layout.addWidget(selected_group)
        
        selected_layout = QHBoxLayout()
        selected_group.setLayout(selected_layout)
        
        self.selected_symbols_list = QListWidget()
        selected_layout.addWidget(self.selected_symbols_list)
        
        # مجموعة إعدادات التداول
        trading_mode_group = QGroupBox("إعدادات التداول")
        symbols_layout.addWidget(trading_mode_group)
        
        mode_layout = QHBoxLayout()
        trading_mode_group.setLayout(mode_layout)
        
        self.trading_mode_combo = QComboBox()
        self.trading_mode_combo.addItems(["تداول جميع الأزواج", "تداول الأزواج المختارة فقط"])
        self.trading_mode_combo.currentIndexChanged.connect(self.change_trading_mode)
        mode_layout.addWidget(self.trading_mode_combo)
        
        # --------------------------
        # محتوى تبويب إدارة الاستراتيجيات الجديد
        # --------------------------
        strategies_layout = QVBoxLayout()
        strategies_tab.setLayout(strategies_layout)
        
        # مجموعة نمط الدمج
        merge_group = QGroupBox("نمط دمج الإشارات")
        strategies_layout.addWidget(merge_group)
        
        merge_layout = QVBoxLayout()
        merge_group.setLayout(merge_layout)
        
        self.merge_mode_combo = QComboBox()
        self.merge_mode_combo.addItems([
            "أي إستراتيجية نشطة",
            "جميع الإستراتيجيات النشطة", 
            "عدد معين من الإستراتيجيات"
        ])
        merge_layout.addWidget(self.merge_mode_combo)
        
        self.required_strategies_spin = QSpinBox()
        self.required_strategies_spin.setRange(1, 10)
        merge_layout.addWidget(QLabel("عدد الإستراتيجيات المطلوبة:"))
        merge_layout.addWidget(self.required_strategies_spin)
        
        # مجموعة تفعيل الاستراتيجيات
        activation_group = QGroupBox("تفعيل الاستراتيجيات")
        strategies_layout.addWidget(activation_group)
        
        activation_layout = QVBoxLayout()
        activation_group.setLayout(activation_layout)
        
        self.strategy_checks = {}
        for strategy in self.strategy_settings:
            cb = QCheckBox(strategy)
            cb.setChecked(True)
            self.strategy_checks[strategy] = cb
            activation_layout.addWidget(cb)
        
        # مجموعة أوزان الاستراتيجيات
        weights_group = QGroupBox("أوزان الاستراتيجيات")
        strategies_layout.addWidget(weights_group)
        
        weights_layout = QFormLayout()
        weights_group.setLayout(weights_layout)
        
        self.strategy_weights = {}
        for strategy in self.strategy_settings:
            sb = QDoubleSpinBox()
            sb.setRange(0.1, 10.0)
            sb.setValue(1.0)
            self.strategy_weights[strategy] = sb
            weights_layout.addRow(strategy, sb)
        
        # مجموعة تحليل الأداء
        analysis_group = QGroupBox("تحليل أداء الاستراتيجيات")
        strategies_layout.addWidget(analysis_group)
        
        analysis_layout = QVBoxLayout()
        analysis_group.setLayout(analysis_layout)
        
        self.performance_table = QTableWidget()
        self.performance_table.setColumnCount(6)
        self.performance_table.setHorizontalHeaderLabels([
            "الاستراتيجية", "عدد الصفقات", "نسبة الربح", 
            "متوسط الربح", "أعلى ربح", "أعلى خسارة"
        ])
        analysis_layout.addWidget(self.performance_table)
        
        # زر تحديث التحليل
        update_analysis_btn = QPushButton("تحديث تحليل الأداء")
        update_analysis_btn.clicked.connect(self.update_performance_analysis)
        analysis_layout.addWidget(update_analysis_btn)
    
    # الدوال الجديدة لإدارة الأزواج
    def load_all_symbols(self):
        try:
            self.all_symbols = []
            exchange_info = self.client.exchange_info()
            for symbol_info in exchange_info['symbols']:
                if symbol_info['quoteAsset'] == 'USDT' and symbol_info['status'] == 'TRADING':
                    self.all_symbols.append(symbol_info['symbol'])
            
            self.all_symbols.sort()
            self.update_symbols_lists()
            self.log_message("تم تحميل جميع الأزواج المتاحة")
        except Exception as e:
            self.log_message(f"خطأ في جلب الأزواج: {str(e)}")

    def update_symbols_lists(self):
        self.all_symbols_list.clear()
        self.selected_symbols_list.clear()
        
        for symbol in self.all_symbols:
            self.all_symbols_list.addItem(symbol)
        
        for symbol in self.selected_symbols:
            self.selected_symbols_list.addItem(symbol)
        
        # تحديد العناصر المختارة في القائمة الرئيسية
        for i in range(self.all_symbols_list.count()):
            item = self.all_symbols_list.item(i)
            if item.text() in self.selected_symbols:
                item.setSelected(True)

    def filter_symbols(self):
        filter_text = self.symbol_filter.text().upper()
        for i in range(self.all_symbols_list.count()):
            item = self.all_symbols_list.item(i)
            item.setHidden(filter_text not in item.text())

    def select_all_symbols(self):
        for i in range(self.all_symbols_list.count()):
            self.all_symbols_list.item(i).setSelected(True)

    def deselect_all_symbols(self):
        for i in range(self.all_symbols_list.count()):
            self.all_symbols_list.item(i).setSelected(False)

    def save_selected_symbols(self):
        selected_items = self.all_symbols_list.selectedItems()
        self.selected_symbols = [item.text() for item in selected_items]
        self.update_symbols_lists()
        self.log_message(f"تم حفظ {len(self.selected_symbols)} زوج للتداول")

    def change_trading_mode(self, index):
        self.trading_mode = "SELECTED" if index == 1 else "ALL"
        mode = "الأزواج المختارة فقط" if index == 1 else "جميع الأزواج"
        self.log_message(f"تم تغيير وضع التداول إلى: {mode}")

    def get_tickers_usdt(self):
        if self.trading_mode == "SELECTED" and self.selected_symbols:
            return self.selected_symbols
        else:
            try:
                tickers = []
                for symbol in self.all_symbols:
                    if symbol.endswith('USDT'):
                        tickers.append(symbol)
                return tickers
            except Exception as e:
                self.log_message(f"خطأ في الحصول على أزواج التداول: {str(e)}")
                return []

    # الدوال الحالية (تم تعديلها لتعمل مع النظام الجديد)
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def update_balance(self):
        try:
            balance = self.get_balance_usdt()
            if balance is not None:
                self.balance_label.setText(f"{balance:.2f} USDT")
        except Exception as e:
            self.log_message(f"خطأ في تحديث الرصيد: {str(e)}")
        
        if self.running:
            QTimer.singleShot(10000, self.update_balance)
    
    def update_open_positions(self):
        try:
            positions = self.get_positions_with_details()
            self.positions_label.setText(str(len(positions)))
            
            self.positions_table.setRowCount(0)
            for pos in positions:
                row = self.positions_table.rowCount()
                self.positions_table.insertRow(row)
                
                self.positions_table.setItem(row, 0, QTableWidgetItem(pos['symbol']))
                self.positions_table.setItem(row, 1, QTableWidgetItem(pos['side']))
                self.positions_table.setItem(row, 2, QTableWidgetItem(str(pos['positionAmt'])))
                self.positions_table.setItem(row, 3, QTableWidgetItem(str(pos['entryPrice'])))
                self.positions_table.setItem(row, 4, QTableWidgetItem(str(pos['unRealizedProfit'])))
                self.positions_table.setItem(row, 5, QTableWidgetItem(str(pos['stopLoss']) if 'stopLoss' in pos else "-"))
                self.positions_table.setItem(row, 6, QTableWidgetItem(pos['time']))
            
        except Exception as e:
            self.log_message(f"خطأ في تحديث الصفقات المفتوحة: {str(e)}")
        
        QTimer.singleShot(5000, self.update_open_positions)
    
    def update_open_orders(self):
        try:
            orders = self.get_open_orders()
            self.orders_label.setText(str(len(orders)))
            
            self.orders_table.setRowCount(0)
            for order in orders:
                row = self.orders_table.rowCount()
                self.orders_table.insertRow(row)
                
                self.orders_table.setItem(row, 0, QTableWidgetItem(order['symbol']))
                self.orders_table.setItem(row, 1, QTableWidgetItem(order['type']))
                self.orders_table.setItem(row, 2, QTableWidgetItem(str(order['origQty'])))
                self.orders_table.setItem(row, 3, QTableWidgetItem(str(order['price'])))
                self.orders_table.setItem(row, 4, QTableWidgetItem(str(order['stopPrice']) if 'stopPrice' in order else "-"))
                self.orders_table.setItem(row, 5, QTableWidgetItem(order['time']))
            
        except Exception as e:
            self.log_message(f"خطأ في تحديث الأوامر المفتوحة: {str(e)}")
        
        QTimer.singleShot(5000, self.update_open_orders)
    
    def add_analysis_result(self, symbol, strategy, price, signal, indicators):
        try:
            row = self.analysis_table.rowCount()
            self.analysis_table.insertRow(row)
            
            self.analysis_table.setItem(row, 0, QTableWidgetItem(symbol))
            self.analysis_table.setItem(row, 1, QTableWidgetItem(strategy))
            self.analysis_table.setItem(row, 2, QTableWidgetItem(f"{price:.4f}"))
            self.analysis_table.setItem(row, 3, QTableWidgetItem(signal))
            
            for i, (key, value) in enumerate(indicators.items(), start=4):
                if i < 7:  # لتجنب تجاوز عدد الأعمدة
                    self.analysis_table.setItem(row, i, QTableWidgetItem(f"{key}: {value}"))
            
            self.analysis_table.setItem(row, 7, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
            
            # الاحتفاظ بآخر 100 تحليل فقط
            if self.analysis_table.rowCount() > 100:
                self.analysis_table.removeRow(0)
                
        except Exception as e:
            self.log_message(f"خطأ في إضافة نتيجة التحليل: {str(e)}")
    
    def start_bot(self):
        if not self.running:
            try:
                # تحديث الإعدادات من الواجهة
                self.current_settings = {
                    'tp': float(self.tp_entry.text()) / 100,
                    'sl': float(self.sl_entry.text()) / 100,
                    'volume': float(self.volume_entry.text()),
                    'leverage': int(self.leverage_entry.text()),
                    'margin_type': self.margin_type_combobox.currentText(),
                    'max_positions': int(self.max_positions_entry.text()),
                    'timeframe': self.timeframe_combobox.currentText(),
                    'strategy': self.strategy_combobox.currentText()
                }
                
                self.running = True
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                self.status_label.setText("يعمل")
                
                # بدء التداول في خيط منفصل
                trading_thread = threading.Thread(target=self.run_bot, daemon=True)
                trading_thread.start()
                
                self.log_message("تم بدء البوت بنجاح")
                self.update_balance()
                
            except Exception as e:
                self.log_message(f"فشل بدء البوت: {str(e)}")
    
    def stop_bot(self):
        if self.running:
            self.running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("متوقف")
            self.log_message("تم إيقاف البوت")
    
    def run_bot(self):
        while self.running:
            try:
                # الحصول على الرصيد والصفقات المفتوحة
                balance = self.get_balance_usdt()
                if balance is None:
                    self.log_message("لا يمكن الاتصال بالAPI. يرجى التحقق من الاتصال")
                    sleep(10)
                    continue
                
                positions = self.get_pos()
                self.positions_label.setText(str(len(positions)))
                
                # إذا كان عدد الصفقات أقل من الحد الأقصى
                if len(positions) < self.current_settings['max_positions']:
                    symbols = self.get_tickers_usdt()
                    
                    if not symbols:
                        self.log_message("لا توجد أزواج متاحة للتداول")
                        sleep(10)
                        continue
                    
                    self.log_message(f"جاري تحليل {len(symbols)} زوج...")
                    
                    for symbol in symbols:
                        if not self.running:
                            break
                            
                        if symbol not in positions:
                            signal = self.check_signal(symbol)
                            
                            if signal == 'buy':
                                self.log_message(f"إشارة شراء قوية لـ {symbol}")
                                if self.execute_trade(symbol, 'buy'):
                                    self.log_message(f"تم تنفيذ أمر الشراء بنجاح لـ {symbol}")
                                else:
                                    self.log_message(f"فشل تنفيذ أمر الشراء لـ {symbol}")
                                sleep(2)
                            
                            elif signal == 'sell':
                                self.log_message(f"إشارة بيع قوية لـ {symbol}")
                                if self.execute_trade(symbol, 'sell'):
                                    self.log_message(f"تم تنفيذ أمر البيع بنجاح لـ {symbol}")
                                else:
                                    self.log_message(f"فشل تنفيذ أمر البيع لـ {symbol}")
                                sleep(2)
                
                sleep(60)  # الانتظار دقيقة قبل الفحص التالي
            
            except Exception as e:
                self.log_message(f"خطأ أثناء تشغيل البوت: {str(e)}")
                sleep(10)
    
    def check_signal(self, symbol):
        try:
            kl = self.klines(symbol)
            if kl is None or kl.empty:
                self.log_message(f"لا توجد بيانات كافية لـ {symbol}")
                return None
                
            signals = {}
            weights = {}
            results = []
            
            # تحقق من الاستراتيجيات المفعلة فقط
            active_strategies = [s for s in self.strategy_checks if self.strategy_checks[s].isChecked()]
            
            for strategy in active_strategies:
                signal = None
                indicators = {}
                
                if strategy == 'EMA + RSI + Volume (الزخم السريع)':
                    signal, indicators = self._ema_rsi_volume(kl, symbol, strategy)
                    
                elif strategy == 'Bollinger Bands + Stochastic (اختناق ثم انفجار)':
                    signal, indicators = self._bollinger_stochastic(kl, symbol, strategy)
                    
                elif strategy == 'VWAP + OBV (تأكيد الحجم)':
                    signal, indicators = self._vwap_obv(kl, symbol, strategy)
                    
                elif strategy == 'EMA Cross Scalping (تقاطع المتوسطات السريع)':
                    signal, indicators = self._ema_cross_scalping(kl, symbol, strategy)
                    
                elif strategy == 'Price Action Scalping (حركة السعر السريعة)':
                    signal, indicators = self._price_action_scalping(kl, symbol, strategy)
                    
                elif strategy == 'Order Flow Scalping (تدفق الأوامر)':
                    signal, indicators = self._order_flow_scalping(kl, symbol, strategy)
                    
                elif strategy == 'Liquidity Grab (السيولة السريعة)':
                    signal, indicators = self._liquidity_grab(kl, symbol, strategy)
                    
                elif strategy == 'Fibonacci Momentum (زخم فيبوناتشي)':
                    signal, indicators = self._fibonacci_momentum(kl, symbol, strategy)
                
                if signal:
                    signals[strategy] = signal
                    weights[strategy] = self.strategy_weights[strategy].value()
                    
                # إضافة النتائج للجدول
                self.add_analysis_result(
                    symbol=symbol,
                    strategy=strategy,
                    price=kl.Close.iloc[-1],
                    signal=signal if signal else "لا إشارة",
                    indicators=indicators
                )
            
            # دمج الإشارات حسب الإعدادات
            merge_mode = self.merge_mode_combo.currentText()
            final_signal = None
            
            if merge_mode == "أي إستراتيجية نشطة" and signals:
                final_signal = self._weighted_signal(signals, weights)
                
            elif merge_mode == "جميع الإستراتيجيات النشطة" and len(signals) == len(active_strategies):
                final_signal = self._weighted_signal(signals, weights)
                
            elif merge_mode == "عدد معين من الإستراتيجيات":
                required = self.required_strategies_spin.value()
                if len(signals) >= required:
                    final_signal = self._weighted_signal(signals, weights)
            
            return final_signal
            
        except Exception as e:
            self.log_message(f"خطأ في تحليل {symbol}: {str(e)}")
            return None
    
    # دوال الاستراتيجيات
    def _ema_rsi_volume(self, kl, symbol, strategy):
        settings = self.strategy_settings[strategy]
        ema_fast = ta.trend.EMAIndicator(kl.Close, window=settings['ema_fast']).ema_indicator()
        ema_slow = ta.trend.EMAIndicator(kl.Close, window=settings['ema_slow']).ema_indicator()
        rsi = ta.momentum.RSIIndicator(kl.Close, window=settings['rsi_length']).rsi()
        
        indicators = {
            "EMA سريع": f"{ema_fast.iloc[-1]:.4f}",
            "EMA بطيء": f"{ema_slow.iloc[-1]:.4f}",
            "RSI": f"{rsi.iloc[-1]:.2f}"
        }
        
        signal = None
        if (kl.Close.iloc[-1] > ema_fast.iloc[-1] and 
            kl.Close.iloc[-1] > ema_slow.iloc[-1] and 
            rsi.iloc[-1] > 50 and 
            rsi.iloc[-2] < settings['rsi_oversold']):
            signal = 'buy'
        
        elif (kl.Close.iloc[-1] < ema_fast.iloc[-1] and 
              kl.Close.iloc[-1] < ema_slow.iloc[-1] and 
              rsi.iloc[-1] < 50 and 
              rsi.iloc[-2] > settings['rsi_overbought']):
            signal = 'sell'
        
        return signal, indicators
    
    def _bollinger_stochastic(self, kl, symbol, strategy):
        settings = self.strategy_settings[strategy]
        bb = ta.volatility.BollingerBands(
            kl.Close, 
            window=settings['bb_length'],
            window_dev=settings['bb_std']
        )
        
        stoch = ta.momentum.StochasticOscillator(
            kl.High, kl.Low, kl.Close,
            window=settings['stoch_length']
        )
        
        indicators = {
            "BB Upper": f"{bb.bollinger_hband().iloc[-1]:.4f}",
            "BB Lower": f"{bb.bollinger_lband().iloc[-1]:.4f}",
            "Stoch K": f"{stoch.stoch().iloc[-1]:.2f}",
            "Stoch D": f"{stoch.stoch_signal().iloc[-1]:.2f}"
        }
        
        signal = None
        if (bb.bollinger_wband().iloc[-1] < 0.2 and
            kl.Close.iloc[-1] > bb.bollinger_hband().iloc[-1] and
            stoch.stoch().iloc[-1] > settings['stoch_oversold'] and
            stoch.stoch_signal().iloc[-1] > settings['stoch_oversold']):
            signal = 'buy'
        
        elif (bb.bollinger_wband().iloc[-1] < 0.2 and
              kl.Close.iloc[-1] < bb.bollinger_lband().iloc[-1] and
              stoch.stoch().iloc[-1] < settings['stoch_overbought'] and
              stoch.stoch_signal().iloc[-1] < settings['stoch_overbought']):
            signal = 'sell'
        
        return signal, indicators
    
    def _vwap_obv(self, kl, symbol, strategy):
        settings = self.strategy_settings[strategy]
        vwap = ta.volume.VolumeWeightedAveragePrice(
            kl.High, kl.Low, kl.Close, kl.Volume,
            window=settings['vwap_length']
        ).volume_weighted_average_price()
        
        obv = ta.volume.OnBalanceVolumeIndicator(kl.Close, kl.Volume).on_balance_volume()
        obv_ema = ta.trend.EMAIndicator(obv, window=settings['obv_ema']).ema_indicator()
        
        indicators = {
            "VWAP": f"{vwap.iloc[-1]:.4f}",
            "OBV": f"{obv.iloc[-1]:.2f}",
            "OBV EMA": f"{obv_ema.iloc[-1]:.2f}"
        }
        
        signal = None
        if (kl.Close.iloc[-1] > vwap.iloc[-1] and 
            obv.iloc[-1] > obv_ema.iloc[-1] and 
            obv.iloc[-1] > obv.iloc[-2]):
            signal = 'buy'
        
        elif (kl.Close.iloc[-1] < vwap.iloc[-1] and 
              obv.iloc[-1] < obv_ema.iloc[-1] and 
              obv.iloc[-1] < obv.iloc[-2]):
            signal = 'sell'
        
        return signal, indicators
    
    def _ema_cross_scalping(self, kl, symbol, strategy):
        settings = self.strategy_settings[strategy]
        ema_vf = ta.trend.EMAIndicator(kl.Close, window=settings['ema_very_fast']).ema_indicator()
        ema_f = ta.trend.EMAIndicator(kl.Close, window=settings['ema_fast']).ema_indicator()
        ema_s = ta.trend.EMAIndicator(kl.Close, window=settings['ema_slow']).ema_indicator()
        
        # حساب نسبة الحجم إلى المتوسط
        volume_avg = kl.Volume.rolling(window=20).mean().iloc[-1]
        volume_ratio = kl.Volume.iloc[-1] / volume_avg
        
        signal = None
        if (ema_vf.iloc[-1] > ema_f.iloc[-1] and 
            ema_f.iloc[-1] > ema_s.iloc[-1] and 
            volume_ratio > settings['volume_threshold']):
            signal = 'buy'
        elif (ema_vf.iloc[-1] < ema_f.iloc[-1] and 
              ema_f.iloc[-1] < ema_s.iloc[-1] and 
              volume_ratio > settings['volume_threshold']):
            signal = 'sell'
        
        indicators = {
            "EMA السريع جداً": f"{ema_vf.iloc[-1]:.4f}",
            "EMA السريع": f"{ema_f.iloc[-1]:.4f}",
            "EMA البطيء": f"{ema_s.iloc[-1]:.4f}",
            "نسبة الحجم": f"{volume_ratio:.2f}"
        }
        
        return signal, indicators
    
    def _price_action_scalping(self, kl, symbol, strategy):
        settings = self.strategy_settings[strategy]
        current = kl.iloc[-1]
        prev = kl.iloc[-2]
        
        # تحديد شمعة البينبار
        is_pinbar = False
        if current.High - max(current.Close, current.Open) > settings['pinbar_threshold'] * (max(current.Close, current.Open) - min(current.Close, current.Open)):
            is_pinbar = True
        
        # تحديد الشمعة الداخلية
        is_inside = (current.High < prev.High and current.Low > prev.Low and 
                    (current.High - current.Low) < settings['inside_bar_ratio'] * (prev.High - prev.Low))
        
        signal = None
        if is_pinbar and current.Close > current.Open and (current.Close - current.Open) > settings['min_body_size']:
            signal = 'buy'
        elif is_pinbar and current.Close < current.Open and (current.Open - current.Close) > settings['min_body_size']:
            signal = 'sell'
        elif is_inside and current.Close > prev.Close:
            signal = 'buy'
        elif is_inside and current.Close < prev.Close:
            signal = 'sell'
        
        indicators = {
            "بينبار": "نعم" if is_pinbar else "لا",
            "شمعة داخلية": "نعم" if is_inside else "لا",
            "حجم الجسم": f"{(current.Close - current.Open):.4f}"
        }
        
        return signal, indicators
    
    def _order_flow_scalping(self, kl, symbol, strategy):
        settings = self.strategy_settings[strategy]
        vwap = ta.volume.VolumeWeightedAveragePrice(
            kl.High, kl.Low, kl.Close, kl.Volume,
            window=20
        ).volume_weighted_average_price()
        
        obv = ta.volume.OnBalanceVolumeIndicator(kl.Close, kl.Volume).on_balance_volume()
        obv_diff = obv.iloc[-1] - obv.iloc[-2]
        
        # حساب نسبة ارتفاع الحجم
        volume_avg = kl.Volume.rolling(window=20).mean().iloc[-1]
        volume_spike = kl.Volume.iloc[-1] / volume_avg
        
        signal = None
        if (kl.Close.iloc[-1] > vwap.iloc[-1] * (1 + settings['vwap_distance']) and 
            obv_diff > settings['obv_threshold'] and 
            volume_spike > settings['volume_spike']):
            signal = 'buy'
        elif (kl.Close.iloc[-1] < vwap.iloc[-1] * (1 - settings['vwap_distance']) and 
              obv_diff < -settings['obv_threshold'] and 
              volume_spike > settings['volume_spike']):
            signal = 'sell'
        
        indicators = {
            "VWAP": f"{vwap.iloc[-1]:.4f}",
            "OBV Change": f"{obv_diff:.0f}",
            "Volume Spike": f"{volume_spike:.2f}x"
        }
        
        return signal, indicators
    
    def _liquidity_grab(self, kl, symbol, strategy):
        settings = self.strategy_settings[strategy]
        current = kl.iloc[-1]
        prev = kl.iloc[-2]
        
        # حساب نسبة الذيل العلوي/السفلي
        upper_wick_ratio = (current.High - max(current.Open, current.Close)) / (current.High - current.Low)
        lower_wick_ratio = (min(current.Open, current.Close) - current.Low) / (current.High - current.Low)
        
        # حساب نسبة الارتداد
        prev_range = prev.High - prev.Low
        current_retrace = (current.Close - prev.Low) / prev_range if current.Close > prev.Close else (prev.High - current.Close) / prev_range
        
        # حساب نسبة ارتفاع الحجم
        volume_avg = kl.Volume.rolling(window=20).mean().iloc[-1]
        volume_confirmation = kl.Volume.iloc[-1] / volume_avg
        
        signal = None
        if (upper_wick_ratio > settings['wick_ratio'] and 
            current_retrace < settings['retracement_depth'] and 
            volume_confirmation > settings['volume_confirmation']):
            signal = 'sell'
        elif (lower_wick_ratio > settings['wick_ratio'] and 
              current_retrace < settings['retracement_depth'] and 
              volume_confirmation > settings['volume_confirmation']):
            signal = 'buy'
        
        indicators = {
            "نسبة الذيل العلوي": f"{upper_wick_ratio:.2f}",
            "نسبة الذيل السفلي": f"{lower_wick_ratio:.2f}",
            "نسبة الارتداد": f"{current_retrace:.2f}",
            "تأكيد الحجم": f"{volume_confirmation:.2f}x"
        }
        
        return signal, indicators
    
    def _fibonacci_momentum(self, kl, symbol, strategy):
        settings = self.strategy_settings[strategy]
        
        # حساب مستويات فيبوناتشي
        recent_high = kl.High.rolling(window=14).max().iloc[-1]
        recent_low = kl.Low.rolling(window=14).min().iloc[-1]
        fib_level = recent_low + (recent_high - recent_low) * settings['fib_level']
        
        # مؤشرات التأكيد
        rsi = ta.momentum.RSIIndicator(kl.Close, window=14).rsi().iloc[-1]
        macd_line = ta.trend.MACD(kl.Close).macd().iloc[-1]
        macd_signal = ta.trend.MACD(kl.Close).macd_signal().iloc[-1]
        macd_diff = macd_line - macd_signal
        
        signal = None
        if (kl.Close.iloc[-1] > fib_level and 
            rsi > settings['rsi_confirm'] and 
            macd_diff > settings['macd_signal']):
            signal = 'buy'
        elif (kl.Close.iloc[-1] < fib_level and 
              rsi < (100 - settings['rsi_confirm']) and 
              macd_diff < -settings['macd_signal']):
            signal = 'sell'
        
        indicators = {
            "مستوى فيبوناتشي": f"{fib_level:.4f}",
            "RSI": f"{rsi:.2f}",
            "فرق MACD": f"{macd_diff:.5f}"
        }
        
        return signal, indicators
    
    def _weighted_signal(self, signals, weights):
        buy_score = 0
        sell_score = 0
        
        for strategy, signal in signals.items():
            if signal == 'buy':
                buy_score += weights[strategy]
            elif signal == 'sell':
                sell_score += weights[strategy]
        
        if buy_score > sell_score and buy_score >= 1.0:
            return 'buy'
        elif sell_score > buy_score and sell_score >= 1.0:
            return 'sell'
        
        return None
    
    def execute_trade(self, symbol, side, strategy=None):
        try:
            # تعيين الرافعة المالية ونوع الهامش
            self.set_mode(symbol, self.current_settings['margin_type'])
            sleep(1)
            self.set_leverage(symbol, self.current_settings['leverage'])
            sleep(1)
            
            # الحصول على السعر الحالي ودقة الكمية
            price = float(self.client.ticker_price(symbol)['price'])
            qty_precision = self.get_qty_precision(symbol)
            price_precision = self.get_price_precision(symbol)
            
            # حساب الكمية
            qty = round(self.current_settings['volume'] / price, qty_precision)
            
            if qty <= 0:
                self.log_message(f"الكمية غير صالحة لـ {symbol}: {qty}")
                return False
            
            if side == 'buy':
                # أمر شراء
                try:
                    if strategy:
                        self.client.new_order(
                            symbol=symbol,
                            side='BUY',
                            type='MARKET',
                            quantity=qty,
                            newClientOrderId=f"{strategy[:20]}_{datetime.now().timestamp()}"
                        )
                    else:
                        self.client.new_order(
                            symbol=symbol,
                            side='BUY',
                            type='MARKET',
                            quantity=qty
                        )
                    self.log_message(f"تم تنفيذ أمر شراء لـ {symbol}")
                    
                    # أوامر وقف الخسارة وجني الربح
                    sl_price = round(price * (1 - self.current_settings['sl']), price_precision)
                    tp_price = round(price * (1 + self.current_settings['tp']), price_precision)
                    
                    self.client.new_order(
                        symbol=symbol,
                        side='SELL',
                        type='STOP_MARKET',
                        quantity=qty,
                        stopPrice=sl_price,
                        closePosition=True
                    )
                    
                    self.client.new_order(
                        symbol=symbol,
                        side='SELL',
                        type='TAKE_PROFIT_MARKET',
                        quantity=qty,
                        stopPrice=tp_price,
                        closePosition=True
                    )
                    
                except Exception as e:
                    self.log_message(f"خطأ في تنفيذ أمر الشراء لـ {symbol}: {str(e)}")
                    return False
                
            elif side == 'sell':
                # أمر بيع
                try:
                    if strategy:
                        self.client.new_order(
                            symbol=symbol,
                            side='SELL',
                            type='MARKET',
                            quantity=qty,
                            newClientOrderId=f"{strategy[:20]}_{datetime.now().timestamp()}"
                        )
                    else:
                        self.client.new_order(
                            symbol=symbol,
                            side='SELL',
                            type='MARKET',
                            quantity=qty
                        )
                    self.log_message(f"تم تنفيذ أمر بيع لـ {symbol}")
                    
                    # أوامر وقف الخسارة وجني الربح
                    sl_price = round(price * (1 + self.current_settings['sl']), price_precision)
                    tp_price = round(price * (1 - self.current_settings['tp']), price_precision)
                    
                    self.client.new_order(
                        symbol=symbol,
                        side='BUY',
                        type='STOP_MARKET',
                        quantity=qty,
                        stopPrice=sl_price,
                        closePosition=True
                    )
                    
                    self.client.new_order(
                        symbol=symbol,
                        side='BUY',
                        type='TAKE_PROFIT_MARKET',
                        quantity=qty,
                        stopPrice=tp_price,
                        closePosition=True
                    )
                    
                except Exception as e:
                    self.log_message(f"خطأ في تنفيذ أمر البيع لـ {symbol}: {str(e)}")
                    return False
            
            # تحديث الجداول بعد الصفقة
            self.update_open_positions()
            self.update_open_orders()
            
            return True
        
        except Exception as e:
            self.log_message(f"خطأ في تنفيذ الصفقة لـ {symbol}: {str(e)}")
            return False
    
    def get_balance_usdt(self):
        try:
            response = self.client.balance(recvWindow=6000)
            for elem in response:
                if elem['asset'] == 'USDT':
                    return float(elem['balance'])
        except ClientError as error:
            self.log_message(f"خطأ في الحصول على الرصيد: {error.error_message}")
            return None
        except Exception as e:
            self.log_message(f"خطأ غير متوقع في الحصول على الرصيد: {str(e)}")
            return None
    
    def klines(self, symbol):
        try:
            resp = pd.DataFrame(self.client.klines(symbol, self.current_settings['timeframe']))
            resp = resp.iloc[:,:6]
            resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            resp = resp.set_index('Time')
            resp.index = pd.to_datetime(resp.index, unit='ms')
            resp = resp.astype(float)
            return resp
        except Exception as e:
            self.log_message(f"خطأ في الحصول على بيانات الشموع لـ {symbol}: {str(e)}")
            return None
    
    def set_leverage(self, symbol, level):
        try:
            self.client.change_leverage(symbol=symbol, leverage=level, recvWindow=6000)
        except Exception as e:
            self.log_message(f"خطأ في تعيين الرافعة لـ {symbol}: {str(e)}")
    
    def set_mode(self, symbol, type):
        try:
            self.client.change_margin_type(symbol=symbol, marginType=type, recvWindow=6000)
        except Exception as e:
            self.log_message(f"خطأ في تعيين نوع الهامش لـ {symbol}: {str(e)}")
    
    def get_price_precision(self, symbol):
        try:
            resp = self.client.exchange_info()['symbols']
            for elem in resp:
                if elem['symbol'] == symbol:
                    return elem['pricePrecision']
            return 2
        except Exception as e:
            self.log_message(f"خطأ في الحصول على دقة السعر لـ {symbol}: {str(e)}")
            return 2
    
    def get_qty_precision(self, symbol):
        try:
            resp = self.client.exchange_info()['symbols']
            for elem in resp:
                if elem['symbol'] == symbol:
                    return elem['quantityPrecision']
            return 3
        except Exception as e:
            self.log_message(f"خطأ في الحصول على دقة الكمية لـ {symbol}: {str(e)}")
            return 3
    
    def get_pos(self):
        try:
            resp = self.client.get_position_risk()
            pos = []
            for elem in resp:
                if float(elem['positionAmt']) != 0:
                    pos.append(elem['symbol'])
            return pos
        except Exception as e:
            self.log_message(f"خطأ في الحصول على الصفقات المفتوحة: {str(e)}")
            return []
    
    def get_positions_with_details(self):
        try:
            positions = []
            resp = self.client.get_position_risk()
            for elem in resp:
                if float(elem['positionAmt']) != 0:
                    position = {
                        'symbol': elem['symbol'],
                        'positionAmt': float(elem['positionAmt']),
                        'entryPrice': float(elem['entryPrice']),
                        'unRealizedProfit': float(elem['unRealizedProfit']),
                        'side': 'BUY' if float(elem['positionAmt']) > 0 else 'SELL',
                        'time': datetime.now().strftime("%H:%M:%S")
                    }
                    
                    # محاولة الحصول على أوامر الوقف لكل صفقة
                    try:
                        orders = self.client.get_orders(symbol=elem['symbol'], recvWindow=6000)
                        for order in orders:
                            if order['type'] == 'STOP_MARKET':
                                position['stopLoss'] = float(order['stopPrice'])
                    except:
                        pass
                    
                    positions.append(position)
            return positions
        except Exception as e:
            self.log_message(f"خطأ في الحصول على تفاصيل الصفقات: {str(e)}")
            return []
    
    def get_open_orders(self):
        try:
            orders = []
            resp = self.client.get_orders(recvWindow=6000)
            for elem in resp:
                order = {
                    'symbol': elem['symbol'],
                    'type': elem['type'],
                    'origQty': float(elem['origQty']),
                    'price': float(elem['price']) if elem['price'] != '0' else '-',
                    'time': datetime.fromtimestamp(elem['time']/1000).strftime("%H:%M:%S")
                }
                
                if 'stopPrice' in elem:
                    order['stopPrice'] = float(elem['stopPrice'])
                
                orders.append(order)
            return orders
        except Exception as e:
            self.log_message(f"خطأ في الحصول على الأوامر المفتوحة: {str(e)}")
            return []
    
    def update_performance_analysis(self):
        try:
            # جلب تاريخ الصفقات من API بينانس
            trades = self.client.get_account_trades(recvWindow=6000)
            
            if not trades:
                return
                
            # تحليل الصفقات حسب الاستراتيجية
            strategy_stats = {}
            
            for trade in trades:
                # استخراج اسم الاستراتيجية من معرف الأمر
                strategy = 'غير معروف'
                if 'clientOrderId' in trade:
                    parts = trade['clientOrderId'].split('_')
                    if len(parts) > 0:
                        strategy = parts[0]
                
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {
                        'count': 0,
                        'wins': 0,
                        'total_profit': 0,
                        'max_profit': 0,
                        'max_loss': 0
                    }
                
                profit = float(trade['realizedPnl'])
                strategy_stats[strategy]['count'] += 1
                strategy_stats[strategy]['total_profit'] += profit
                
                if profit > 0:
                    strategy_stats[strategy]['wins'] += 1
                    if profit > strategy_stats[strategy]['max_profit']:
                        strategy_stats[strategy]['max_profit'] = profit
                else:
                    if profit < strategy_stats[strategy]['max_loss']:
                        strategy_stats[strategy]['max_loss'] = profit
            
            # عرض النتائج في الجدول
            self.performance_table.setRowCount(0)
            
            for strategy, stats in strategy_stats.items():
                row = self.performance_table.rowCount()
                self.performance_table.insertRow(row)
                
                win_rate = (stats['wins'] / stats['count']) * 100 if stats['count'] > 0 else 0
                avg_profit = stats['total_profit'] / stats['count'] if stats['count'] > 0 else 0
                
                self.performance_table.setItem(row, 0, QTableWidgetItem(strategy))
                self.performance_table.setItem(row, 1, QTableWidgetItem(str(stats['count'])))
                self.performance_table.setItem(row, 2, QTableWidgetItem(f"{win_rate:.2f}%"))
                self.performance_table.setItem(row, 3, QTableWidgetItem(f"{avg_profit:.4f}"))
                self.performance_table.setItem(row, 4, QTableWidgetItem(f"{stats['max_profit']:.4f}"))
                self.performance_table.setItem(row, 5, QTableWidgetItem(f"{stats['max_loss']:.4f}"))
                
        except Exception as e:
            self.log_message(f"خطأ في تحليل الأداء: {str(e)}")
    
    def close_open_orders(self, symbol):
        try:
            self.client.cancel_open_orders(symbol=symbol, recvWindow=6000)
        except Exception as e:
            self.log_message(f"خطأ في إغلاق الأوامر لـ {symbol}: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    bot_gui = TradingBotGUI()
    bot_gui.show()
    sys.exit(app.exec_())
