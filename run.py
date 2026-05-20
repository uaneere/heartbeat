#!/usr/bin/env python3
"""
Запуск API сервера для генерации музыки
"""

import uvicorn
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запуск Heartbeat API")
    parser.add_argument("--host", default="0.0.0.0", help="Хост для запуска")
    parser.add_argument("--port", type=int, default=8000, help="Порт для запуска")
    parser.add_argument("--reload", action="store_true", help="Автоматическая перезагрузка при изменениях")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )