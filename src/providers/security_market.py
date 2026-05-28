from __future__ import annotations


def resolve_security_market(stock_code: str) -> str:
    code = str(stock_code or "").strip()
    if code.isdigit() and len(code) == 5:
        return "hk"
    if code.startswith(("0", "3")) and code.isdigit() and len(code) == 6:
        return "sz"
    if code.startswith(("5", "6", "9")) and code.isdigit() and len(code) == 6:
        return "sh"
    return "unknown"


def is_hong_kong_stock_code(stock_code: str) -> bool:
    return resolve_security_market(stock_code) == "hk"


def yahoo_symbol_for_stock(stock_code: str) -> str:
    code = str(stock_code or "").strip()
    market = resolve_security_market(code)
    if market == "hk":
        return f"{int(code):04d}.HK"
    if market == "sh":
        return f"{code}.SS"
    return f"{code}.SZ"


def eastmoney_a_share_secid(stock_code: str) -> str | None:
    code = str(stock_code or "").strip()
    market = resolve_security_market(code)
    if market == "sh":
        return f"1.{code}"
    if market == "sz":
        return f"0.{code}"
    return None


def eastmoney_a_share_secucode(stock_code: str) -> str | None:
    code = str(stock_code or "").strip()
    market = resolve_security_market(code)
    if market == "sh":
        return f"{code}.SH"
    if market == "sz":
        return f"{code}.SZ"
    return None


def tushare_a_share_ts_code(stock_code: str) -> str | None:
    return eastmoney_a_share_secucode(stock_code)
