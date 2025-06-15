<p align="center">
  <img src="https://static1.e926.net/data/3e/77/3e7745cd94b602804eeb5a6880e89d64.jpg" /> </br>
  <s><i align="center">Tag yourself, I'm the femboy</i></s>

  <h1 align="center">AWP</h1>
  <p align="center">A bot for ████████. Only does the execution, not very friendly to use.</p>
  <p align="center">Maybe you wanted to see <a href="https://github.com/rorre/kesiangan">Kesiangan</a> instead?</p>
</p>

## How to use

uh

```
python -m awp --cmd run --config someconfig.yaml
```

Config definition can be seen [here](https://github.com/rorre/awp/blob/master/awp/config.py#L14-L26). You may want to use kesiangan to generate the config.

## Notable difference to existing projects

Of course, there are various other ████ war bot in GitHub and many other places. So what's special with this one? To put it simply: other bots make use of some sort of browser and a browser controller (puppeteer, selenium, playwright, yadayada). This one doesn't do that, and instead request to the endpoint directly.

**It is the same request as what a browser would do**, just without the browser part. This saves some bandwidth as there is no need to download the images, CSS, JS, etc. **It's also why it's quite trivial to detect these kind of bots**. If you are building a website, and someone just shoots into "interesting" endpoints, are they really human?
