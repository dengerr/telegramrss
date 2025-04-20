from go import cfg

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('app:app', host="0.0.0.0", port=int(cfg.get('http', 'port')), reload=True)
