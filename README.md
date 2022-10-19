# Option-research
Analyze multiple trading strategies on options.


## Installation
```
pip install -r requirements.txt
```

### Path generation:
This command will generate paths for the simulation into runGen folder. For more information run this command with ```--help``` argument.
```
python3 generateRuns.py --saveDir <output_path> -p <num_path> --pricesFile Gemini_ETHUSD1h_unixFix.csv
```
```<output_path>```: directory where your run generations will be stored (generateRuns) already exists as a default
```<num_paths>```  : number of paths you wish to generate for your simulation runs
This will generate <num_path>.pickle file.

## Simulate strategy
Now, we can run the strategy simulation on the generated paths:
For more information run this command with ```--help``` argument.

Default strategy (Without hedging strategy)
```
python3 runStrategy.py -m 1.0 0.5  -s 0.8 1.0  -c 2 --saveDir <outputFolder> -r <num_path>.pickle --strategy AbstractStrategy --ivc 0.05 --initPrice 2000 --calls
```

Hedging strategy
```
python3 runStrategy.py -m 1.0 0.5  -s 0.8 1.0  -c 2 --saveDir <outputFolder> -r <num_path>.pickle --strategy DeltaIntervalHedgeStrategy --ivc 0.05 --initPrice 2000 --calls  --strategyArgs 1:h " -0.4:float" " -0.5:float"
```

## Strategies

### AbstractStrategy
This strategy does not apply any hedging during the simulation.

### DeltaIntervalHedgeStrategy
This strategy tries to keep the delta of the pool inside the given interval.

Example how to run:
```
python3 runStrategy.py -m 1.0  -s 0.8  -c 4 --saveDir runGen -r runGen/100.pickle --strategy DeltaIntervalHedgeStrategy --ivc 0.05 --initPrice 2000 --calls  --strategyArgs 1:h " -0.4:float" " -0.5:float"
```
### DeltaNonPositiveHedgeStrategy
This strategy keeps delta negative only, but within defined range.

Example how to run:
```
python3 runStrategy.py -m 1.0  -s 0.8  -c 4 --saveDir runGen -r runGen/100.pickle --strategy DeltaNonPositiveHedgeStrategy --ivc 0.05 --initPrice 2000 --calls  --strategyArgs 1:h " -0.5:float" 
```

## Output Files
- **unStdPaths** -> unstardatize distribution based on mu and sigma
- **prices** -> paths of prices
- **dfs** and **pool_values**: (contain information about run paths):
  - **dfs**
    - epoch_id: path id
    - market_index: current series of options
    - volume_buy: trade size calls in ETH, puts in USD
    - implied_vol: current IV
    - reserve_b: number of btokens
    - reserve_w: number of wtokens
    - underlying_price: current price of asset
    - theoretical_price: theoretical price of current option
    - strike: strike of current options 
    - pool_position_delta: current total delta of pool
    - per_position_delta: current total delta of perpetuals
  - **pool_values**
    - date: current date
    - epoch_id: path id
    - pool_value_usd: current pool value in USD
    - pool_value: current pool value in underlying asset
    - hedge_value: hedge value in USD
    - settled_pool_value: pool_value after settlement of all contracts
    - buyerShare: 
    - writerShare: 
    - collateral_reserve: pool collateral reserve


## Graph generation
You can generate graphs using the createGraphs.ipynb.
Just edit *parameters* section with correct values.


