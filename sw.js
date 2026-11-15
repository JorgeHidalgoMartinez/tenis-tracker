const CACHE='tenistracker-shell-v2';
self.addEventListener('install',evt=>{evt.waitUntil(caches.open(CACHE).then(c=>c.addAll(['./','./index.html','./assets/icon.svg'])));self.skipWaiting()});
self.addEventListener('activate',evt=>{evt.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',evt=>{const u=new URL(evt.request.url);if(u.pathname.endsWith('/data/torneos.json')){evt.respondWith(fetch(evt.request).catch(()=>caches.match(evt.request)));return}if(evt.request.method==='GET'&&u.origin===self.location.origin){evt.respondWith(fetch(evt.request).catch(()=>caches.match(evt.request)));}});
