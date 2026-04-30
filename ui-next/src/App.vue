<template>
  <div class="app">
    <nav class="app-nav">
      <span class="app-logo">WtPy Demo</span>
      <router-link to="/backtest" class="nav-link">回测分析</router-link>
      <router-link to="/monitor" class="nav-link">实盘监控</router-link>
    </nav>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0f0f1e;
  color: #9ab;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
}
</style>

<style scoped>
.app { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
.app-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 20px;
  height: 46px;
  background: #16213e;
  border-bottom: 1px solid #2d2d44;
  flex-shrink: 0;
}
.app-logo {
  font-size: 15px;
  font-weight: 700;
  color: #26a69a;
  margin-right: 12px;
}
.nav-link {
  color: #6a7a8a;
  text-decoration: none;
  font-size: 14px;
  padding: 5px 12px;
  border-radius: 4px;
  transition: color 0.15s;
}
.nav-link:hover { color: #9ab; }
.nav-link.router-link-active { color: #26a69a; background: #1a3040; }
.app-main { flex: 1; overflow: hidden; }
</style>
