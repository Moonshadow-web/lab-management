// vite.config.js
import { defineConfig } from "file:///D:/workbuddyprojects/%E7%BD%91%E9%A1%B5%E7%89%88-%E7%94%9F%E5%85%8D%E9%80%9F%E6%9F%A5%E5%B7%A5%E5%85%B7/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///D:/workbuddyprojects/%E7%BD%91%E9%A1%B5%E7%89%88-%E7%94%9F%E5%85%8D%E9%80%9F%E6%9F%A5%E5%B7%A5%E5%85%B7/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import { fileURLToPath, URL } from "node:url";
var __vite_injected_original_import_meta_url = "file:///D:/workbuddyprojects/%E7%BD%91%E9%A1%B5%E7%89%88-%E7%94%9F%E5%85%8D%E9%80%9F%E6%9F%A5%E5%B7%A5%E5%85%B7/frontend/vite.config.js";
var vite_config_default = defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", __vite_injected_original_import_meta_url)) }
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8123", changeOrigin: true },
      "/uploads": { target: "http://localhost:8123", changeOrigin: true }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFx3b3JrYnVkZHlwcm9qZWN0c1xcXFxcdTdGNTFcdTk4NzVcdTcyNDgtXHU3NTFGXHU1MTREXHU5MDFGXHU2N0U1XHU1REU1XHU1MTc3XFxcXGZyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJEOlxcXFx3b3JrYnVkZHlwcm9qZWN0c1xcXFxcdTdGNTFcdTk4NzVcdTcyNDgtXHU3NTFGXHU1MTREXHU5MDFGXHU2N0U1XHU1REU1XHU1MTc3XFxcXGZyb250ZW5kXFxcXHZpdGUuY29uZmlnLmpzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9EOi93b3JrYnVkZHlwcm9qZWN0cy8lRTclQkQlOTElRTklQTElQjUlRTclODklODgtJUU3JTk0JTlGJUU1JTg1JThEJUU5JTgwJTlGJUU2JTlGJUE1JUU1JUI3JUE1JUU1JTg1JUI3L2Zyb250ZW5kL3ZpdGUuY29uZmlnLmpzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcbmltcG9ydCB2dWUgZnJvbSAnQHZpdGVqcy9wbHVnaW4tdnVlJ1xuaW1wb3J0IHsgZmlsZVVSTFRvUGF0aCwgVVJMIH0gZnJvbSAnbm9kZTp1cmwnXG5cbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XG4gIHBsdWdpbnM6IFt2dWUoKV0sXG4gIHJlc29sdmU6IHtcbiAgICBhbGlhczogeyAnQCc6IGZpbGVVUkxUb1BhdGgobmV3IFVSTCgnLi9zcmMnLCBpbXBvcnQubWV0YS51cmwpKSB9LFxuICB9LFxuICBzZXJ2ZXI6IHtcbiAgICBob3N0OiB0cnVlLFxuICAgIHBvcnQ6IDUxNzMsXG4gICAgcHJveHk6IHtcbiAgICAgICcvYXBpJzogeyB0YXJnZXQ6ICdodHRwOi8vbG9jYWxob3N0OjgxMjMnLCBjaGFuZ2VPcmlnaW46IHRydWUgfSxcbiAgICAgICcvdXBsb2Fkcyc6IHsgdGFyZ2V0OiAnaHR0cDovL2xvY2FsaG9zdDo4MTIzJywgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXG4gICAgfSxcbiAgfSxcbn0pXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQTBYLFNBQVMsb0JBQW9CO0FBQ3ZaLE9BQU8sU0FBUztBQUNoQixTQUFTLGVBQWUsV0FBVztBQUY0SixJQUFNLDJDQUEyQztBQUloUCxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTLENBQUMsSUFBSSxDQUFDO0FBQUEsRUFDZixTQUFTO0FBQUEsSUFDUCxPQUFPLEVBQUUsS0FBSyxjQUFjLElBQUksSUFBSSxTQUFTLHdDQUFlLENBQUMsRUFBRTtBQUFBLEVBQ2pFO0FBQUEsRUFDQSxRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixPQUFPO0FBQUEsTUFDTCxRQUFRLEVBQUUsUUFBUSx5QkFBeUIsY0FBYyxLQUFLO0FBQUEsTUFDOUQsWUFBWSxFQUFFLFFBQVEseUJBQXlCLGNBQWMsS0FBSztBQUFBLElBQ3BFO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
