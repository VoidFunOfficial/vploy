import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from backend.sys_configs.global_event_reg import vlogger
from backend.polymarket_api import GammaMarketsAPI
from backend.purse import get_purse
from .db_manager import RecordDBManager

class RecordManager:
    def __init__(self):
        self.db = RecordDBManager()

    def update_info(self, market_id: str, side: str, end_date: str, operation: str, price: float, amount: float, tips: str = ""):
        """
        Record investment operation.

        Args:
            market_id (str): Market ID
            side (str): 'YES' or 'NO'
            end_date (str): Market end date (yyyy-mm-dd)
            operation (str): 'BUY', 'SELL', or 'SETTLE'
            price (float): Operation price per share
            amount (float): Number of shares (not currency value)
            tips (str, optional): Remarks
        """
        try:
            self.db.add_operation(market_id, side, end_date, operation, price, amount, tips)
        except Exception as e:
            vlogger.error("RECORD.UPDATE_INFO.ERROR", msg="Failed to update info", extra={
                "market_id": market_id,
                "error": str(e)
            })
            raise

    def get_info(self, market_id: str) -> List[Dict]:
        """
        Get all historical operations for a market.
        
        Args:
            market_id (str): Market ID
            
        Returns:
            List[Dict]: List of operations
        """
        return self.db.get_operations(market_id)

    def get_today_total_profit(self) -> float:
        """
        Calculate total unrealized profit for all active positions.
        
        Returns:
            float: Total unrealized profit
        """
        total_profit = 0.0
        
        try:
            # 1. Get all market IDs
            market_ids = self.db.get_all_market_ids()
            if not market_ids:
                return 0.0

            # 2. Iterate markets and calculate holding
            with GammaMarketsAPI() as api:
                for market_id in market_ids:
                    # Get history
                    ops = self.db.get_operations(market_id)
                    if not ops:
                        continue
                        
                    # Calculate holding for YES and NO separately (though usually one per market)
                    holdings = self._calculate_holdings(ops)
                    
                    if not holdings:
                        continue
                        
                    # Get current price
                    try:
                        market = api.get_market_by_id(market_id)
                        if not market or not market.outcome_prices:
                            vlogger.warn("RECORD.PROFIT.NO_PRICE", msg="Market price not found", extra={"market_id": market_id})
                            continue
                            
                        # Parse market prices using helper
                        price_map = self._get_market_prices(market)
                        if not price_map:
                            continue
                        
                        # Calculate profit for this market
                        for side, data in holdings.items():
                            shares = data['shares']
                            cost = data['cost']
                            
                            if shares <= 0.0001: # Ignore dust
                                continue
                                
                            current_price = price_map.get(side.upper())
                            if current_price is None:
                                continue
                                
                            current_value = shares * current_price
                            pnl = current_value - cost
                            total_profit += pnl
                            
                    except Exception as e:
                        vlogger.warn("RECORD.PROFIT.MARKET_ERROR", msg="Error calculating profit for market", extra={
                            "market_id": market_id,
                            "error": str(e)
                        })
                        continue

            return total_profit

        except Exception as e:
            vlogger.error("RECORD.PROFIT.ERROR", msg="Failed to get today profit", extra={"error": str(e)})
            return 0.0

    def _get_market_prices(self, market: Any) -> Dict[str, float]:
        """
        Parse market outcomes and prices to get a mapping of Side -> Price.
        Handles JSON parsing for fields defined as strings in polymarket_types.py.
        """
        try:
            # 1. Parse outcomes
            outcomes = market.outcomes
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except json.JSONDecodeError:
                    vlogger.warn("RECORD.PARSE.OUTCOMES_ERROR", msg="Failed to parse outcomes JSON", extra={"market_id": market.id, "outcomes": outcomes})
                    return {}
            
            if not isinstance(outcomes, list):
                return {}

            # 2. Parse prices
            prices = market.outcome_prices
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except json.JSONDecodeError:
                    vlogger.warn("RECORD.PARSE.PRICES_ERROR", msg="Failed to parse prices JSON", extra={"market_id": market.id, "prices": prices})
                    return {}
            
            if not isinstance(prices, list) or len(prices) != len(outcomes):
                return {}

            # 3. Map to YES/NO
            price_map = {}
            for i, outcome in enumerate(outcomes):
                try:
                    price_val = float(prices[i])
                    outcome_str = str(outcome).upper()
                    
                    if "YES" in outcome_str:
                        price_map["YES"] = price_val
                    elif "NO" in outcome_str:
                        price_map["NO"] = price_val
                except (ValueError, TypeError):
                    continue
            
            return price_map
            
        except Exception as e:
            vlogger.error("RECORD.PARSE.ERROR", msg="Unexpected error parsing market data", extra={"error": str(e), "market_id": getattr(market, 'id', 'unknown')})
            return {}

    def record_today(self, update_data: int, new_invest: int, profit_today: float, settled_today: int, locked_amount: float, available_amount: float):
        """
        Record daily summary.

        Args:
            update_data (int): Number of operations today
            new_invest (int): Number of markets recorded today
            profit_today (float): Total unrealized profit
            settled_today (int): Number of markets settled today
            locked_amount (float): Current locked funds
            available_amount (float): Current available funds
        """
        try:
            self.db.add_daily_summary(update_data, new_invest, profit_today, settled_today, locked_amount, available_amount)
        except Exception as e:
            vlogger.error("RECORD.RECORD_TODAY.ERROR", msg="Failed to record today", extra={"error": str(e)})
            raise
    def auto_settle(self) -> Dict[str, Any]:
        """
        Automatically settle positions that have reached their settlement date.

        Returns:
            Dict[str, Any]: Settlement results including:
                - settled_count: Number of positions settled
                - settled_markets: Number of unique markets settled
                - errors: List of error messages
        """
        settled_count = 0
        settled_markets = set()
        errors = []

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            market_ids = self.db.get_all_market_ids()

            if not market_ids:
                vlogger.info("RECORD.AUTO_SETTLE.NO_MARKETS", msg="No markets to settle")
                return {"settled_count": 0, "settled_markets": 0, "errors": []}

            with GammaMarketsAPI() as api:
                for market_id in market_ids:
                    try:
                        # Get operations history
                        ops = self.db.get_operations(market_id)
                        if not ops:
                            continue

                        # Calculate current holdings
                        holdings = self._calculate_holdings(ops)
                        if not holdings:
                            continue

                        # Check if already settled
                        has_settle = any(op['operation'].upper() == 'SETTLE' for op in ops)
                        if has_settle:
                            continue

                        # Get end_date from operations
                        end_date = None
                        for op in ops:
                            if op.get('end_date'):
                                end_date = op['end_date']
                                break

                        if not end_date:
                            continue

                        # Check if settlement date has passed
                        try:
                            settle_date = datetime.strptime(end_date, "%Y-%m-%d")
                            print(settle_date.date(), datetime.now().date())
                            if settle_date.date() > datetime.now().date():
                                continue  # Not yet time to settle
                        except ValueError:
                            vlogger.warn("RECORD.AUTO_SETTLE.DATE_ERROR", msg="Invalid end_date format", extra={
                                "market_id": market_id,
                                "end_date": end_date
                            })
                            continue

                        # Get market current status
                        market = api.get_market_by_id(market_id)
                        if not market:
                            vlogger.warn("RECORD.AUTO_SETTLE.MARKET_NOT_FOUND", msg="Market not found", extra={
                                "market_id": market_id
                            })
                            continue

                    

                        # Get final prices
                        price_map = self._get_market_prices(market)
                        if not price_map:
                            vlogger.warn("RECORD.AUTO_SETTLE.NO_PRICES", msg="No prices available", extra={
                                "market_id": market_id
                            })
                            continue

                        # Settle each side
                        for side, data in holdings.items():
                            shares = data['shares']
                            cost = data['cost']

                            if shares <= 0.0001:  # Ignore dust
                                continue

                            final_price = price_map.get(side.upper())
                            if final_price is None:
                                continue

                            # Final price should be 0 or 1 for settled markets
                            if final_price not in [0.0, 1.0]:
                                vlogger.warn("RECORD.AUTO_SETTLE.INVALID_PRICE", msg="Final price not 0 or 1", extra={
                                    "market_id": market_id,
                                    "side": side,
                                    "price": final_price
                                })
                                continue

                            # Calculate settlement
                            # amount field stores shares
                            settlement_shares = shares

                            # Record SETTLE operation (amount = shares)
                            self.update_info(
                                market_id=market_id,
                                side=side,
                                end_date=end_date,
                                operation='SETTLE',
                                price=final_price,
                                amount=settlement_shares,
                                tips=f"Auto-settled on {today}"
                            )

                            settled_count += 1
                            settled_markets.add(market_id)  # Track unique markets settled

                            vlogger.info("RECORD.AUTO_SETTLE.SUCCESS", msg="Position settled", extra={
                                "market_id": market_id,
                                "side": side,
                                "shares": shares,
                                "final_price": final_price
                            })

                    except Exception as e:
                        error_msg = f"Error settling market {market_id}: {str(e)}"
                        errors.append(error_msg)
                        vlogger.error("RECORD.AUTO_SETTLE.MARKET_ERROR", msg=error_msg, extra={
                            "market_id": market_id,
                            "error": str(e)
                        })
                        continue

            vlogger.info("RECORD.AUTO_SETTLE.COMPLETE", msg="Auto settlement completed", extra={
                "settled_count": settled_count,
                "settled_markets": len(settled_markets),
                "errors_count": len(errors)
            })

            return {
                "settled_count": settled_count,
                "settled_markets": len(settled_markets),
                "errors": errors
            }

        except Exception as e:
            vlogger.error("RECORD.AUTO_SETTLE.ERROR", msg="Auto settlement failed", extra={
                "error": str(e)
            })
            return {
                "settled_count": settled_count,
                "settled_markets": len(settled_markets),
                "errors": errors + [str(e)]
            }

    def record_daily(self) -> bool:
        """
        Record daily summary automatically.

        Calculates and records:
        - Today's total profit (unrealized profit in currency)
        - Number of markets settled today
        - Number of markets recorded today (via update_info)
        - Current locked and available funds

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            # Get yesterday's summary for comparison
            last_record = self.db.get_daily_summary(yesterday)

            # Calculate today's total profit (unrealized)
            profit_today = self.get_today_total_profit()

            # Calculate settled market count today (number of markets with SETTLE operations)
            settle_ops = self.db.get_settle_operations_by_date(today)
            settled_market_ids = set(op['market_id'] for op in settle_ops)
            settled_today = len(settled_market_ids)

            # Calculate new recorded market count today (number of markets with any operations)
            today_ops = self.db.get_operations_by_date(today)
            recorded_market_ids = set(op['market_id'] for op in today_ops)
            new_invest = len(recorded_market_ids)

            # Get current fund status from purse
            purse = get_purse()
            status = purse.get_status()
            locked_amount = status.get('locked_fund', 0.0)
            available_amount = status.get('available_cash', 0.0)

            # Count of operations today
            update_count = len(today_ops)

            # Record to database
            self.record_today(
                update_data=update_count,
                new_invest=new_invest,
                profit_today=profit_today,
                settled_today=settled_today,
                locked_amount=locked_amount,
                available_amount=available_amount
            )

            vlogger.info("RECORD.DAILY.SUCCESS", msg="Daily summary recorded successfully", extra={
                "date": today,
                "update_count": update_count,
                "new_invest": new_invest,
                "profit_today": profit_today,
                "settled_today": settled_today,
                "locked_amount": locked_amount,
                "available_amount": available_amount
            })

            return True

        except Exception as e:
            vlogger.error("RECORD.DAILY.ERROR", msg="Failed to record daily summary", extra={
                "error": str(e)
            })
            return False

    def generate_today_report(self) -> Dict[str, Any]:
        """
        Generate today's trading and profit report.

        Returns:
            Dict[str, Any]: Report containing:
                - date: Report date
                - new_invest: Number of markets recorded today
                - profit_today: Today's unrealized profit (currency)
                - settled_today: Number of markets settled today
                - locked_amount: Current locked funds
                - available_amount: Current available funds
                - total_fund: Total funds
                - active_positions: Number of active positions
                - settled_positions: Number of settled positions today
                - operations_count: Total operations today
                - report_text: Formatted report string
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            # Get today's summary
            summary = self.db.get_daily_summary(today)

            # If no summary exists, create one
            if not summary:
                self.record_daily()
                summary = self.db.get_daily_summary(today)

            if not summary:
                return {
                    "error": "Failed to generate or retrieve daily summary",
                    "date": today
                }

            # Get purse status
            purse = get_purse()
            status = purse.get_status()

            # Count active positions
            market_ids = self.db.get_all_market_ids()
            active_positions = 0

            for market_id in market_ids:
                ops = self.db.get_operations(market_id)
                holdings = self._calculate_holdings(ops)

                for side, data in holdings.items():
                    if data['shares'] > 0.0001:
                        active_positions += 1

            # Count settled positions today
            settle_ops = self.db.get_settle_operations_by_date(today)
            settled_positions = len(settle_ops)

            # Build report
            report = {
                "date": today,
                "new_invest": summary.get('new_invest', 0.0),
                "profit_today": summary.get('profit_today', 0.0),
                "settled_today": summary.get('settled_today', 0.0),
                "locked_amount": summary.get('locked_amount', 0.0),
                "available_amount": summary.get('available_amount', 0.0),
                "total_fund": status.get('total_fund', 0.0),
                "active_positions": active_positions,
                "settled_positions": settled_positions,
                "operations_count": summary.get('update_count', 0)
            }

            # Generate formatted text report
            report_lines = [
                f"=== Daily Report for {today} ===",
                f"",
                f"Fund Status:",
                f"  Total Fund:      ${report['total_fund']:.2f}",
                f"  Available Cash:  ${report['available_amount']:.2f}",
                f"  Locked Fund:     ${report['locked_amount']:.2f}",
                f"",
                f"Today's Activity:",
                f"  Markets Recorded: {report['new_invest']}",
                f"  Markets Settled:  {report['settled_today']}",
                f"  Unrealized P&L:   ${report['profit_today']:.2f}",
                f"",
                f"Positions:",
                f"  Active:           {report['active_positions']}",
                f"  Settled Today:    {report['settled_positions']}",
                f"",
                f"Operations:         {report['operations_count']}",
                f"",
                f"================================"
            ]

            report['report_text'] = "\n".join(report_lines)

            vlogger.info("RECORD.REPORT.GENERATED", msg="Daily report generated", extra={
                "date": today,
                "active_positions": active_positions,
                "settled_positions": settled_positions
            })

            return report

        except Exception as e:
            vlogger.error("RECORD.REPORT.ERROR", msg="Failed to generate report", extra={
                "error": str(e)
            })
            return {
                "error": str(e),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
    def get_today_detail_report(self) -> Dict[str, Any]:
        """
        Generate today's detailed trading report.

        Returns:
            Dict[str, Any]: Detailed report containing:
                - summary: Today's summary report (from generate_today_report)
                - operations: List of all operations today with details
                    - id: Operation ID
                    - market_id: Market ID
                    - side: YES or NO
                    - end_date: Settlement date
                    - operation: BUY, SELL, or SETTLE
                    - price: Operation price
                    - amount: Number of shares
                    - tips: Operation remarks
                    - created_at: Operation timestamp
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            # Get today's summary report
            summary_report = self.generate_today_report()

            # Get all operations today
            today_ops = self.db.get_operations_by_date(today)

            # Format operations list
            operations_list = []
            for op in today_ops:
                operations_list.append({
                    "id": op.get('id'),
                    "market_id": op.get('market_id'),
                    "side": op.get('side'),
                    "end_date": op.get('end_date'),
                    "operation": op.get('operation'),
                    "price": op.get('price'),
                    "shares": op.get('amount'),
                    "tips": op.get('tips', ''),
                    "created_at": op.get('created_at')
                })

            # Build detailed report
            detailed_report = {
                "date": today,
                "summary": summary_report,
                "operations": operations_list,
                "operations_count": len(operations_list)
            }

            vlogger.info("RECORD.DETAIL_REPORT.GENERATED", msg="Detailed report generated", extra={
                "date": today,
                "operations_count": len(operations_list)
            })

            return detailed_report

        except Exception as e:
            vlogger.error("RECORD.DETAIL_REPORT.ERROR", msg="Failed to generate detailed report", extra={
                "error": str(e)
            })
            return {
                "error": str(e),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "summary": {},
                "operations": []
            }

    def _calculate_holdings(self, ops: List[Dict]) -> Dict[str, Dict[str, float]]:
        """
        Calculate current holdings (shares and cost) from operations history.

        Note: 'amount' field stores the number of shares, not currency value.

        Returns: { 'YES': {'shares': 100, 'cost': 50}, 'NO': ... }
        """
        holdings = {} # side -> {shares, cost}

        for op in ops:
            side = op['side'].upper()
            op_type = op['operation'].upper()
            price = op['price']
            amount = op['amount']  # Number of shares

            if side not in holdings:
                holdings[side] = {'shares': 0.0, 'cost': 0.0}

            if op_type == 'BUY':
                # amount is shares, cost is shares * price
                shares = amount
                cost = amount * price
                holdings[side]['shares'] += shares
                holdings[side]['cost'] += cost

            elif op_type == 'SELL':
                # amount is shares sold
                shares_sold = amount

                # Reduce cost proportionally (Weighted Average)
                current_shares = holdings[side]['shares']
                current_cost = holdings[side]['cost']

                if current_shares > 0:
                    avg_cost_per_share = current_cost / current_shares
                    cost_reduced = avg_cost_per_share * shares_sold

                    holdings[side]['shares'] -= shares_sold
                    holdings[side]['cost'] -= cost_reduced

                    # Prevent negative values due to rounding errors
                    if holdings[side]['shares'] < 0:
                        holdings[side]['shares'] = 0
                        holdings[side]['cost'] = 0

            elif op_type == 'SETTLE':
                # Settlement means position is closed/converted to cash
                # Clear the position
                holdings[side]['shares'] = 0
                holdings[side]['cost'] = 0

        return holdings
