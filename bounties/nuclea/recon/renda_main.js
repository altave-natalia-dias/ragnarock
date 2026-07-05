/******/ var __webpack_modules__ = ({

/***/ 84429:
/*!*********************!*\
  !*** ./src/main.ts ***!
  \*********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony import */ var _angular_architects_module_federation__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @angular-architects/module-federation */ 45888);

Promise.all([(0,_angular_architects_module_federation__WEBPACK_IMPORTED_MODULE_0__.loadRemoteEntry)({
  type: 'module',
  remoteEntry: 'http://localhost:5101/remoteEntry.js'
})]).catch(err => console.error('Error loading remote entries', err)).then(() => __webpack_require__.e(/*! import() */ 20).then(__webpack_require__.bind(__webpack_require__, /*! ./bootstrap */ 55020))).catch(err => console.error(err));

/***/ }),

/***/ 45888:
/*!******************************************************************************************************************************!*\
  !*** ./node_modules/@angular-architects/module-federation-runtime/fesm2020/angular-architects-module-federation-runtime.mjs ***!
  \******************************************************************************************************************************/
/***/ ((__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   getManifest: () => (/* binding */ getManifest),
/* harmony export */   initFederation: () => (/* binding */ initFederation),
/* harmony export */   loadManifest: () => (/* binding */ loadManifest),
/* harmony export */   loadRemoteEntry: () => (/* binding */ loadRemoteEntry),
/* harmony export */   loadRemoteModule: () => (/* binding */ loadRemoteModule),
/* harmony export */   setManifest: () => (/* binding */ setManifest)
/* harmony export */ });
/* harmony import */ var _w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./node_modules/@babel/runtime/helpers/esm/asyncToGenerator.js */ 10467);

let config = {};
const containerMap = {};
const remoteMap = {};
let isDefaultScopeInitialized = false;
function lookupExposedModule(_x, _x2) {
  return _lookupExposedModule.apply(this, arguments);
}
function _lookupExposedModule() {
  _lookupExposedModule = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (key, exposedModule) {
    const container = containerMap[key];
    const factory = yield container.get(exposedModule);
    const Module = factory();
    return Module;
  });
  return _lookupExposedModule.apply(this, arguments);
}
function initRemote(_x3, _x4) {
  return _initRemote.apply(this, arguments);
}
function _initRemote() {
  _initRemote = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (container, key) {
    // const container = window[key] as Container;
    // Do we still need to initialize the remote?
    if (remoteMap[key]) {
      return container;
    }
    // Do we still need to initialize the share scope?
    if (!isDefaultScopeInitialized) {
      yield __webpack_require__.I('default');
      isDefaultScopeInitialized = true;
    }
    yield container.init(__webpack_require__.S.default);
    remoteMap[key] = true;
    return container;
  });
  return _initRemote.apply(this, arguments);
}
function loadRemoteEntry(_x5, _x6) {
  return _loadRemoteEntry.apply(this, arguments);
}
function _loadRemoteEntry() {
  _loadRemoteEntry = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (remoteEntryOrOptions, remoteName) {
    if (typeof remoteEntryOrOptions === 'string') {
      const remoteEntry = remoteEntryOrOptions;
      return yield loadRemoteScriptEntry(remoteEntry, remoteName);
    } else if (remoteEntryOrOptions.type === 'script') {
      const options = remoteEntryOrOptions;
      return yield loadRemoteScriptEntry(options.remoteEntry, options.remoteName);
    } else if (remoteEntryOrOptions.type === 'module') {
      const options = remoteEntryOrOptions;
      yield loadRemoteModuleEntry(options.remoteEntry);
    }
  });
  return _loadRemoteEntry.apply(this, arguments);
}
function loadRemoteModuleEntry(_x7) {
  return _loadRemoteModuleEntry.apply(this, arguments);
}
function _loadRemoteModuleEntry() {
  _loadRemoteModuleEntry = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (remoteEntry) {
    if (containerMap[remoteEntry]) {
      return Promise.resolve();
    }
    return yield import( /* webpackIgnore:true */remoteEntry).then(container => {
      initRemote(container, remoteEntry);
      containerMap[remoteEntry] = container;
    });
  });
  return _loadRemoteModuleEntry.apply(this, arguments);
}
function loadRemoteScriptEntry(_x8, _x9) {
  return _loadRemoteScriptEntry.apply(this, arguments);
}
function _loadRemoteScriptEntry() {
  _loadRemoteScriptEntry = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (remoteEntry, remoteName) {
    return new Promise((resolve, reject) => {
      // Is remoteEntry already loaded?
      if (containerMap[remoteName]) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = remoteEntry;
      script.onerror = reject;
      script.onload = () => {
        const container = window[remoteName];
        initRemote(container, remoteName);
        containerMap[remoteName] = container;
        resolve();
      };
      document.body.appendChild(script);
    });
  });
  return _loadRemoteScriptEntry.apply(this, arguments);
}
function loadRemoteModule(_x0, _x1) {
  return _loadRemoteModule.apply(this, arguments);
}
function _loadRemoteModule() {
  _loadRemoteModule = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (optionsOrRemoteName, exposedModule) {
    let loadRemoteEntryOptions;
    let key;
    let remoteEntry;
    let options;
    if (typeof optionsOrRemoteName === 'string') {
      options = {
        type: 'manifest',
        remoteName: optionsOrRemoteName,
        exposedModule: exposedModule
      };
    } else {
      options = optionsOrRemoteName;
    }
    // To support legacy API (< ng 13)
    if (!options.type) {
      const hasManifest = Object.keys(config).length > 0;
      options.type = hasManifest ? 'manifest' : 'script';
    }
    if (options.type === 'manifest') {
      const manifestEntry = config[options.remoteName];
      if (!manifestEntry) {
        throw new Error('Manifest does not contain ' + options.remoteName);
      }
      options = {
        type: manifestEntry.type,
        exposedModule: options.exposedModule,
        remoteEntry: manifestEntry.remoteEntry,
        remoteName: manifestEntry.type === 'script' ? options.remoteName : undefined
      };
      remoteEntry = manifestEntry.remoteEntry;
    } else {
      remoteEntry = options.remoteEntry;
    }
    if (options.type === 'script') {
      loadRemoteEntryOptions = {
        type: 'script',
        remoteEntry: options.remoteEntry,
        remoteName: options.remoteName
      };
      key = options.remoteName;
    } else if (options.type === 'module') {
      loadRemoteEntryOptions = {
        type: 'module',
        remoteEntry: options.remoteEntry
      };
      key = options.remoteEntry;
    }
    if (remoteEntry) {
      yield loadRemoteEntry(loadRemoteEntryOptions);
    }
    return yield lookupExposedModule(key, options.exposedModule);
  });
  return _loadRemoteModule.apply(this, arguments);
}
function setManifest(_x10) {
  return _setManifest.apply(this, arguments);
}
function _setManifest() {
  _setManifest = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (manifest, skipRemoteEntries = false) {
    config = parseConfig(manifest);
    if (!skipRemoteEntries) {
      yield loadRemoteEntries();
    }
  });
  return _setManifest.apply(this, arguments);
}
function getManifest() {
  return config;
}
function initFederation(_x11) {
  return _initFederation.apply(this, arguments);
}
function _initFederation() {
  _initFederation = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (manifest, skipRemoteEntries = false) {
    if (typeof manifest === 'string') {
      return loadManifest(manifest, skipRemoteEntries);
    } else {
      return setManifest(manifest, skipRemoteEntries);
    }
  });
  return _initFederation.apply(this, arguments);
}
function loadManifest(_x12) {
  return _loadManifest.apply(this, arguments);
}
function _loadManifest() {
  _loadManifest = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* (configFile, skipRemoteEntries = false) {
    const result = yield fetch(configFile);
    if (!result.ok) {
      throw Error('could not load configFile: ' + configFile);
    }
    config = parseConfig(yield result.json());
    if (!skipRemoteEntries) {
      yield loadRemoteEntries();
    }
  });
  return _loadManifest.apply(this, arguments);
}
function parseConfig(config) {
  const result = {};
  for (const key in config) {
    const value = config[key];
    let entry;
    if (typeof value === 'string') {
      entry = {
        remoteEntry: value,
        type: 'module'
      };
    } else {
      entry = {
        ...value,
        type: value.type || 'module'
      };
    }
    result[key] = entry;
  }
  return result;
}
function loadRemoteEntries() {
  return _loadRemoteEntries.apply(this, arguments);
}
/**
 * Generated bundle index. Do not edit.
 */
function _loadRemoteEntries() {
  _loadRemoteEntries = (0,_w_regimob_parcr_comcl_front_regimob_parcr_comcl_front_node_modules_babel_runtime_helpers_esm_asyncToGenerator_js__WEBPACK_IMPORTED_MODULE_0__["default"])(function* () {
    const promises = [];
    for (const key in config) {
      const entry = config[key];
      if (entry.type === 'module') {
        promises.push(loadRemoteEntry({
          type: 'module',
          remoteEntry: entry.remoteEntry
        }));
      } else {
        promises.push(loadRemoteEntry({
          type: 'script',
          remoteEntry: entry.remoteEntry,
          remoteName: key
        }));
      }
    }
    yield Promise.all(promises);
  });
  return _loadRemoteEntries.apply(this, arguments);
}

//# sourceMappingURL=angular-architects-module-federation-runtime.mjs.map

/***/ }),

/***/ 10467:
/*!*********************************************************************!*\
  !*** ./node_modules/@babel/runtime/helpers/esm/asyncToGenerator.js ***!
  \*********************************************************************/
/***/ ((__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (/* binding */ _asyncToGenerator)
/* harmony export */ });
function asyncGeneratorStep(gen, resolve, reject, _next, _throw, key, arg) {
  try {
    var info = gen[key](arg);
    var value = info.value;
  } catch (error) {
    reject(error);
    return;
  }
  if (info.done) {
    resolve(value);
  } else {
    Promise.resolve(value).then(_next, _throw);
  }
}
function _asyncToGenerator(fn) {
  return function () {
    var self = this,
      args = arguments;
    return new Promise(function (resolve, reject) {
      var gen = fn.apply(self, args);
      function _next(value) {
        asyncGeneratorStep(gen, resolve, reject, _next, _throw, "next", value);
      }
      function _throw(err) {
        asyncGeneratorStep(gen, resolve, reject, _next, _throw, "throw", err);
      }
      _next(undefined);
    });
  };
}

/***/ })

/******/ });
/************************************************************************/
/******/ // The module cache
/******/ var __webpack_module_cache__ = {};
/******/ 
/******/ // The require function
/******/ function __webpack_require__(moduleId) {
/******/ 	// Check if module is in cache
/******/ 	var cachedModule = __webpack_module_cache__[moduleId];
/******/ 	if (cachedModule !== undefined) {
/******/ 		return cachedModule.exports;
/******/ 	}
/******/ 	// Create a new module (and put it into the cache)
/******/ 	var module = __webpack_module_cache__[moduleId] = {
/******/ 		id: moduleId,
/******/ 		loaded: false,
/******/ 		exports: {}
/******/ 	};
/******/ 
/******/ 	// Execute the module function
/******/ 	__webpack_modules__[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/ 
/******/ 	// Flag the module as loaded
/******/ 	module.loaded = true;
/******/ 
/******/ 	// Return the exports of the module
/******/ 	return module.exports;
/******/ }
/******/ 
/******/ // expose the modules object (__webpack_modules__)
/******/ __webpack_require__.m = __webpack_modules__;
/******/ 
/******/ // expose the module cache
/******/ __webpack_require__.c = __webpack_module_cache__;
/******/ 
/************************************************************************/
/******/ /* webpack/runtime/compat get default export */
/******/ (() => {
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = (module) => {
/******/ 		var getter = module && module.__esModule ?
/******/ 			() => (module['default']) :
/******/ 			() => (module);
/******/ 		__webpack_require__.d(getter, { a: getter });
/******/ 		return getter;
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/create fake namespace object */
/******/ (() => {
/******/ 	var getProto = Object.getPrototypeOf ? (obj) => (Object.getPrototypeOf(obj)) : (obj) => (obj.__proto__);
/******/ 	var leafPrototypes;
/******/ 	// create a fake namespace object
/******/ 	// mode & 1: value is a module id, require it
/******/ 	// mode & 2: merge all properties of value into the ns
/******/ 	// mode & 4: return value when already ns object
/******/ 	// mode & 16: return value when it's Promise-like
/******/ 	// mode & 8|1: behave like require
/******/ 	__webpack_require__.t = function(value, mode) {
/******/ 		if(mode & 1) value = this(value);
/******/ 		if(mode & 8) return value;
/******/ 		if(typeof value === 'object' && value) {
/******/ 			if((mode & 4) && value.__esModule) return value;
/******/ 			if((mode & 16) && typeof value.then === 'function') return value;
/******/ 		}
/******/ 		var ns = Object.create(null);
/******/ 		__webpack_require__.r(ns);
/******/ 		var def = {};
/******/ 		leafPrototypes = leafPrototypes || [null, getProto({}), getProto([]), getProto(getProto)];
/******/ 		for(var current = mode & 2 && value; typeof current == 'object' && !~leafPrototypes.indexOf(current); current = getProto(current)) {
/******/ 			Object.getOwnPropertyNames(current).forEach((key) => (def[key] = () => (value[key])));
/******/ 		}
/******/ 		def['default'] = () => (value);
/******/ 		__webpack_require__.d(ns, def);
/******/ 		return ns;
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/define property getters */
/******/ (() => {
/******/ 	// define getter functions for harmony exports
/******/ 	__webpack_require__.d = (exports, definition) => {
/******/ 		for(var key in definition) {
/******/ 			if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 				Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 			}
/******/ 		}
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/ensure chunk */
/******/ (() => {
/******/ 	__webpack_require__.f = {};
/******/ 	// This file contains only the entry chunk.
/******/ 	// The chunk loading function for additional chunks
/******/ 	__webpack_require__.e = (chunkId) => {
/******/ 		return Promise.all(Object.keys(__webpack_require__.f).reduce((promises, key) => {
/******/ 			__webpack_require__.f[key](chunkId, promises);
/******/ 			return promises;
/******/ 		}, []));
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/get javascript chunk filename */
/******/ (() => {
/******/ 	// This function allow to reference async chunks
/******/ 	__webpack_require__.u = (chunkId) => {
/******/ 		// return url for filenames based on template
/******/ 		return "" + (chunkId === 58 ? "quill" : chunkId) + "." + {"20":"c96594cb0c5732b7","58":"0ff962509dac7db2","177":"14cf31430a6525b8","245":"00a39586139cf928","275":"4d24ce2882b4bd06","282":"29b81fb8b0c9f146","372":"caacaabdce4997d7","558":"d478fe62d0e3d48f","626":"3274cbcb57d90e2e","627":"6447502e85f6cc01","656":"c6893c479ffc7ff6","705":"25dba87aa6070d9a","901":"c06bc350228b76c7"}[chunkId] + ".js";
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/get mini-css chunk filename */
/******/ (() => {
/******/ 	// This function allow to reference async chunks
/******/ 	__webpack_require__.miniCssF = (chunkId) => {
/******/ 		// return url for filenames based on template
/******/ 		return undefined;
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/hasOwnProperty shorthand */
/******/ (() => {
/******/ 	__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ })();
/******/ 
/******/ /* webpack/runtime/load script */
/******/ (() => {
/******/ 	var inProgress = {};
/******/ 	var dataWebpackPrefix = "regimob-parcr-comcl-front:";
/******/ 	// loadScript function to load a script via script tag
/******/ 	__webpack_require__.l = (url, done, key, chunkId) => {
/******/ 		if(inProgress[url]) { inProgress[url].push(done); return; }
/******/ 		var script, needAttach;
/******/ 		if(key !== undefined) {
/******/ 			var scripts = document.getElementsByTagName("script");
/******/ 			for(var i = 0; i < scripts.length; i++) {
/******/ 				var s = scripts[i];
/******/ 				if(s.getAttribute("src") == url || s.getAttribute("data-webpack") == dataWebpackPrefix + key) { script = s; break; }
/******/ 			}
/******/ 		}
/******/ 		if(!script) {
/******/ 			needAttach = true;
/******/ 			script = document.createElement('script');
/******/ 			script.type = "module";
/******/ 			script.charset = 'utf-8';
/******/ 			script.timeout = 120;
/******/ 			if (__webpack_require__.nc) {
/******/ 				script.setAttribute("nonce", __webpack_require__.nc);
/******/ 			}
/******/ 			script.setAttribute("data-webpack", dataWebpackPrefix + key);
/******/ 	
/******/ 			script.src = __webpack_require__.tu(url);
/******/ 		}
/******/ 		inProgress[url] = [done];
/******/ 		var onScriptComplete = (prev, event) => {
/******/ 			// avoid mem leaks in IE.
/******/ 			script.onerror = script.onload = null;
/******/ 			clearTimeout(timeout);
/******/ 			var doneFns = inProgress[url];
/******/ 			delete inProgress[url];
/******/ 			script.parentNode && script.parentNode.removeChild(script);
/******/ 			doneFns && doneFns.forEach((fn) => (fn(event)));
/******/ 			if(prev) return prev(event);
/******/ 		}
/******/ 		var timeout = setTimeout(onScriptComplete.bind(null, undefined, { type: 'timeout', target: script }), 120000);
/******/ 		script.onerror = onScriptComplete.bind(null, script.onerror);
/******/ 		script.onload = onScriptComplete.bind(null, script.onload);
/******/ 		needAttach && document.head.appendChild(script);
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/make namespace object */
/******/ (() => {
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = (exports) => {
/******/ 		if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 			Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		}
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/node module decorator */
/******/ (() => {
/******/ 	__webpack_require__.nmd = (module) => {
/******/ 		module.paths = [];
/******/ 		if (!module.children) module.children = [];
/******/ 		return module;
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/sharing */
/******/ (() => {
/******/ 	__webpack_require__.S = {};
/******/ 	var initPromises = {};
/******/ 	var initTokens = {};
/******/ 	__webpack_require__.I = (name, initScope) => {
/******/ 		if(!initScope) initScope = [];
/******/ 		// handling circular init calls
/******/ 		var initToken = initTokens[name];
/******/ 		if(!initToken) initToken = initTokens[name] = {};
/******/ 		if(initScope.indexOf(initToken) >= 0) return;
/******/ 		initScope.push(initToken);
/******/ 		// only runs once
/******/ 		if(initPromises[name]) return initPromises[name];
/******/ 		// creates a new share scope if needed
/******/ 		if(!__webpack_require__.o(__webpack_require__.S, name)) __webpack_require__.S[name] = {};
/******/ 		// runs all init snippets from all modules reachable
/******/ 		var scope = __webpack_require__.S[name];
/******/ 		var warn = (msg) => {
/******/ 			if (typeof console !== "undefined" && console.warn) console.warn(msg);
/******/ 		};
/******/ 		var uniqueName = "regimob-parcr-comcl-front";
/******/ 		var register = (name, version, factory, eager) => {
/******/ 			var versions = scope[name] = scope[name] || {};
/******/ 			var activeVersion = versions[version];
/******/ 			if(!activeVersion || (!activeVersion.loaded && (!eager != !activeVersion.eager ? eager : uniqueName > activeVersion.from))) versions[version] = { get: factory, from: uniqueName, eager: !!eager };
/******/ 		};
/******/ 		var initExternal = (id) => {
/******/ 			var handleError = (err) => (warn("Initialization of sharing external failed: " + err));
/******/ 			try {
/******/ 				var module = __webpack_require__(id);
/******/ 				if(!module) return;
/******/ 				var initFn = (module) => (module && module.init && module.init(__webpack_require__.S[name], initScope))
/******/ 				if(module.then) return promises.push(module.then(initFn, handleError));
/******/ 				var initResult = initFn(module);
/******/ 				if(initResult && initResult.then) return promises.push(initResult['catch'](handleError));
/******/ 			} catch(err) { handleError(err); }
/******/ 		}
/******/ 		var promises = [];
/******/ 		switch(name) {
/******/ 			case "default": {
/******/ 				register("@angular/common/http", "16.2.12", () => (__webpack_require__.e(626).then(() => (() => (__webpack_require__(/*! ./node_modules/@angular/common/fesm2022/http.mjs */ 21626))))));
/******/ 				register("@angular/common", "16.2.12", () => (__webpack_require__.e(177).then(() => (() => (__webpack_require__(/*! ./node_modules/@angular/common/fesm2022/common.mjs */ 60177))))));
/******/ 				register("@angular/core", "16.2.12", () => (__webpack_require__.e(705).then(() => (() => (__webpack_require__(/*! ./node_modules/@angular/core/fesm2022/core.mjs */ 17705))))));
/******/ 				register("@angular/router", "16.2.12", () => (__webpack_require__.e(901).then(() => (() => (__webpack_require__(/*! ./node_modules/@angular/router/fesm2022/router.mjs */ 7901))))));
/******/ 				register("@nucleasa-uxui/ds-portais-externos", "2.74.4", () => (__webpack_require__.e(656).then(() => (() => (__webpack_require__(/*! ./node_modules/@nucleasa-uxui/ds-portais-externos/fesm2022/nucleasa-uxui-ds-portais-externos.mjs */ 37656))))));
/******/ 			}
/******/ 			break;
/******/ 		}
/******/ 		if(!promises.length) return initPromises[name] = 1;
/******/ 		return initPromises[name] = Promise.all(promises).then(() => (initPromises[name] = 1));
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/trusted types policy */
/******/ (() => {
/******/ 	var policy;
/******/ 	__webpack_require__.tt = () => {
/******/ 		// Create Trusted Type policy if Trusted Types are available and the policy doesn't exist yet.
/******/ 		if (policy === undefined) {
/******/ 			policy = {
/******/ 				createScriptURL: (url) => (url)
/******/ 			};
/******/ 			if (typeof trustedTypes !== "undefined" && trustedTypes.createPolicy) {
/******/ 				policy = trustedTypes.createPolicy("angular#bundler", policy);
/******/ 			}
/******/ 		}
/******/ 		return policy;
/******/ 	};
/******/ })();
/******/ 
/******/ /* webpack/runtime/trusted types script url */
/******/ (() => {
/******/ 	__webpack_require__.tu = (url) => (__webpack_require__.tt().createScriptURL(url));
/******/ })();
/******/ 
/******/ /* webpack/runtime/publicPath */
/******/ (() => {
/******/ 	var scriptUrl;
/******/ 	if (typeof import.meta.url === "string") scriptUrl = import.meta.url
/******/ 	// When supporting browsers where an automatic publicPath is not supported you must specify an output.publicPath manually via configuration
/******/ 	// or pass an empty string ("") and set the __webpack_public_path__ variable from your code to use your own logic.
/******/ 	if (!scriptUrl) throw new Error("Automatic publicPath is not supported in this browser");
/******/ 	scriptUrl = scriptUrl.replace(/#.*$/, "").replace(/\?.*$/, "").replace(/\/[^\/]+$/, "/");
/******/ 	__webpack_require__.p = scriptUrl;
/******/ })();
/******/ 
/******/ /* webpack/runtime/consumes */
/******/ (() => {
/******/ 	var parseVersion = (str) => {
/******/ 		// see webpack/lib/util/semver.js for original code
/******/ 		var p=p=>{return p.split(".").map((p=>{return+p==p?+p:p}))},n=/^([^-+]+)?(?:-([^+]+))?(?:\+(.+))?$/.exec(str),r=n[1]?p(n[1]):[];return n[2]&&(r.length++,r.push.apply(r,p(n[2]))),n[3]&&(r.push([]),r.push.apply(r,p(n[3]))),r;
/******/ 	}
/******/ 	var versionLt = (a, b) => {
/******/ 		// see webpack/lib/util/semver.js for original code
/******/ 		a=parseVersion(a),b=parseVersion(b);for(var r=0;;){if(r>=a.length)return r<b.length&&"u"!=(typeof b[r])[0];var e=a[r],n=(typeof e)[0];if(r>=b.length)return"u"==n;var t=b[r],f=(typeof t)[0];if(n!=f)return"o"==n&&"n"==f||("s"==f||"u"==n);if("o"!=n&&"u"!=n&&e!=t)return e<t;r++}
/******/ 	}
/******/ 	var rangeToString = (range) => {
/******/ 		// see webpack/lib/util/semver.js for original code
/******/ 		var r=range[0],n="";if(1===range.length)return"*";if(r+.5){n+=0==r?">=":-1==r?"<":1==r?"^":2==r?"~":r>0?"=":"!=";for(var e=1,a=1;a<range.length;a++){e--,n+="u"==(typeof(t=range[a]))[0]?"-":(e>0?".":"")+(e=2,t)}return n}var g=[];for(a=1;a<range.length;a++){var t=range[a];g.push(0===t?"not("+o()+")":1===t?"("+o()+" || "+o()+")":2===t?g.pop()+" "+g.pop():rangeToString(t))}return o();function o(){return g.pop().replace(/^\((.+)\)$/,"$1")}
/******/ 	}
/******/ 	var satisfy = (range, version) => {
/******/ 		// see webpack/lib/util/semver.js for original code
/******/ 		if(0 in range){version=parseVersion(version);var e=range[0],r=e<0;r&&(e=-e-1);for(var n=0,i=1,a=!0;;i++,n++){var f,s,g=i<range.length?(typeof range[i])[0]:"";if(n>=version.length||"o"==(s=(typeof(f=version[n]))[0]))return!a||("u"==g?i>e&&!r:""==g!=r);if("u"==s){if(!a||"u"!=g)return!1}else if(a)if(g==s)if(i<=e){if(f!=range[i])return!1}else{if(r?f>range[i]:f<range[i])return!1;f!=range[i]&&(a=!1)}else if("s"!=g&&"n"!=g){if(r||i<=e)return!1;a=!1,i--}else{if(i<=e||s<g!=r)return!1;a=!1}else"s"!=g&&"n"!=g&&(a=!1,i--)}}var t=[],o=t.pop.bind(t);for(n=1;n<range.length;n++){var u=range[n];t.push(1==u?o()|o():2==u?o()&o():u?satisfy(u,version):!o())}return!!o();
/******/ 	}
/******/ 	var exists = (scope, key) => {
/******/ 		return scope && __webpack_require__.o(scope, key);
/******/ 	}
/******/ 	var get = (entry) => {
/******/ 		entry.loaded = 1;
/******/ 		return entry.get()
/******/ 	};
/******/ 	var eagerOnly = (versions) => {
/******/ 		return Object.keys(versions).reduce((filtered, version) => {
/******/ 				if (versions[version].eager) {
/******/ 					filtered[version] = versions[version];
/******/ 				}
/******/ 				return filtered;
/******/ 		}, {});
/******/ 	};
/******/ 	var findLatestVersion = (scope, key, eager) => {
/******/ 		var versions = eager ? eagerOnly(scope[key]) : scope[key];
/******/ 		var key = Object.keys(versions).reduce((a, b) => {
/******/ 			return !a || versionLt(a, b) ? b : a;
/******/ 		}, 0);
/******/ 		return key && versions[key];
/******/ 	};
/******/ 	var findSatisfyingVersion = (scope, key, requiredVersion, eager) => {
/******/ 		var versions = eager ? eagerOnly(scope[key]) : scope[key];
/******/ 		var key = Object.keys(versions).reduce((a, b) => {
/******/ 			if (!satisfy(requiredVersion, b)) return a;
/******/ 			return !a || versionLt(a, b) ? b : a;
/******/ 		}, 0);
/******/ 		return key && versions[key]
/******/ 	};
/******/ 	var findSingletonVersionKey = (scope, key, eager) => {
/******/ 		var versions = eager ? eagerOnly(scope[key]) : scope[key];
/******/ 		return Object.keys(versions).reduce((a, b) => {
/******/ 			return !a || (!versions[a].loaded && versionLt(a, b)) ? b : a;
/******/ 		}, 0);
/******/ 	};
/******/ 	var getInvalidSingletonVersionMessage = (scope, key, version, requiredVersion) => {
/******/ 		return "Unsatisfied version " + version + " from " + (version && scope[key][version].from) + " of shared singleton module " + key + " (required " + rangeToString(requiredVersion) + ")"
/******/ 	};
/******/ 	var getInvalidVersionMessage = (scope, scopeName, key, requiredVersion, eager) => {
/******/ 		var versions = scope[key];
/******/ 		return "No satisfying version (" + rangeToString(requiredVersion) + ")" + (eager ? " for eager consumption" : "") + " of shared module " + key + " found in shared scope " + scopeName + ".\n" +
/******/ 			"Available versions: " + Object.keys(versions).map((key) => {
/******/ 			return key + " from " + versions[key].from;
/******/ 		}).join(", ");
/******/ 	};
/******/ 	var fail = (msg) => {
/******/ 		throw new Error(msg);
/******/ 	}
/******/ 	var failAsNotExist = (scopeName, key) => {
/******/ 		return fail("Shared module " + key + " doesn't exist in shared scope " + scopeName);
/******/ 	}
/******/ 	var warn = /*#__PURE__*/ (msg) => {
/******/ 		if (typeof console !== "undefined" && console.warn) console.warn(msg);
/******/ 	};
/******/ 	var init = (fn) => (function(scopeName, key, eager, c, d) {
/******/ 		var promise = __webpack_require__.I(scopeName);
/******/ 		if (promise && promise.then && !eager) {
/******/ 			return promise.then(fn.bind(fn, scopeName, __webpack_require__.S[scopeName], key, false, c, d));
/******/ 		}
/******/ 		return fn(scopeName, __webpack_require__.S[scopeName], key, eager, c, d);
/******/ 	});
/******/ 	
/******/ 	var useFallback = (scopeName, key, fallback) => {
/******/ 		return fallback ? fallback() : failAsNotExist(scopeName, key);
/******/ 	}
/******/ 	var load = /*#__PURE__*/ init((scopeName, scope, key, eager, fallback) => {
/******/ 		if (!exists(scope, key)) return useFallback(scopeName, key, fallback);
/******/ 		return get(findLatestVersion(scope, key, eager));
/******/ 	});
/******/ 	var loadVersion = /*#__PURE__*/ init((scopeName, scope, key, eager, requiredVersion, fallback) => {
/******/ 		if (!exists(scope, key)) return useFallback(scopeName, key, fallback);
/******/ 		var satisfyingVersion = findSatisfyingVersion(scope, key, requiredVersion, eager);
/******/ 		if (satisfyingVersion) return get(satisfyingVersion);
/******/ 		warn(getInvalidVersionMessage(scope, scopeName, key, requiredVersion, eager))
/******/ 		return get(findLatestVersion(scope, key, eager));
/******/ 	});
/******/ 	var loadStrictVersion = /*#__PURE__*/ init((scopeName, scope, key, eager, requiredVersion, fallback) => {
/******/ 		if (!exists(scope, key)) return useFallback(scopeName, key, fallback);
/******/ 		var satisfyingVersion = findSatisfyingVersion(scope, key, requiredVersion, eager);
/******/ 		if (satisfyingVersion) return get(satisfyingVersion);
/******/ 		if (fallback) return fallback();
/******/ 		fail(getInvalidVersionMessage(scope, scopeName, key, requiredVersion, eager));
/******/ 	});
/******/ 	var loadSingleton = /*#__PURE__*/ init((scopeName, scope, key, eager, fallback) => {
/******/ 		if (!exists(scope, key)) return useFallback(scopeName, key, fallback);
/******/ 		var version = findSingletonVersionKey(scope, key, eager);
/******/ 		return get(scope[key][version]);
/******/ 	});
/******/ 	var loadSingletonVersion = /*#__PURE__*/ init((scopeName, scope, key, eager, requiredVersion, fallback) => {
/******/ 		if (!exists(scope, key)) return useFallback(scopeName, key, fallback);
/******/ 		var version = findSingletonVersionKey(scope, key, eager);
/******/ 		if (!satisfy(requiredVersion, version)) {
/******/ 			warn(getInvalidSingletonVersionMessage(scope, key, version, requiredVersion));
/******/ 		}
/******/ 		return get(scope[key][version]);
/******/ 	});
/******/ 	var loadStrictSingletonVersion = /*#__PURE__*/ init((scopeName, scope, key, eager, requiredVersion, fallback) => {
/******/ 		if (!exists(scope, key)) return useFallback(scopeName, key, fallback);
/******/ 		var version = findSingletonVersionKey(scope, key, eager);
/******/ 		if (!satisfy(requiredVersion, version)) {
/******/ 			fail(getInvalidSingletonVersionMessage(scope, key, version, requiredVersion));
/******/ 		}
/******/ 		return get(scope[key][version]);
/******/ 	});
/******/ 	var installedModules = {};
/******/ 	var moduleToHandlerMapping = {
/******/ 		14332: () => (loadSingletonVersion("default", "@angular/core", false, [1,"auto"], () => (__webpack_require__.e(705).then(() => (() => (__webpack_require__(/*! @angular/core */ 17705))))))),
/******/ 		84482: () => (loadSingletonVersion("default", "@angular/common", false, [1,"auto"], () => (__webpack_require__.e(558).then(() => (() => (__webpack_require__(/*! @angular/common */ 60177))))))),
/******/ 		54230: () => (loadSingletonVersion("default", "@angular/common/http", false, [1,"auto"], () => (__webpack_require__.e(245).then(() => (() => (__webpack_require__(/*! @angular/common/http */ 21626))))))),
/******/ 		34294: () => (loadSingletonVersion("default", "@angular/router", false, [1,"auto"], () => (__webpack_require__.e(282).then(() => (() => (__webpack_require__(/*! @angular/router */ 7901))))))),
/******/ 		97803: () => (loadSingletonVersion("default", "@nucleasa-uxui/ds-portais-externos", false, [1,"auto"], () => (__webpack_require__.e(275).then(() => (() => (__webpack_require__(/*! @nucleasa-uxui/ds-portais-externos */ 37656)))))))
/******/ 	};
/******/ 	// no consumes in initial chunks
/******/ 	var chunkMapping = {
/******/ 		"20": [
/******/ 			14332,
/******/ 			84482,
/******/ 			54230,
/******/ 			34294,
/******/ 			97803
/******/ 		],
/******/ 		"177": [
/******/ 			14332
/******/ 		],
/******/ 		"626": [
/******/ 			14332,
/******/ 			84482
/******/ 		],
/******/ 		"656": [
/******/ 			14332,
/******/ 			34294,
/******/ 			54230,
/******/ 			84482
/******/ 		],
/******/ 		"901": [
/******/ 			14332,
/******/ 			54230,
/******/ 			84482
/******/ 		]
/******/ 	};
/******/ 	var startedInstallModules = {};
/******/ 	__webpack_require__.f.consumes = (chunkId, promises) => {
/******/ 		if(__webpack_require__.o(chunkMapping, chunkId)) {
/******/ 			chunkMapping[chunkId].forEach((id) => {
/******/ 				if(__webpack_require__.o(installedModules, id)) return promises.push(installedModules[id]);
/******/ 				if(!startedInstallModules[id]) {
/******/ 				var onFactory = (factory) => {
/******/ 					installedModules[id] = 0;
/******/ 					__webpack_require__.m[id] = (module) => {
/******/ 						delete __webpack_require__.c[id];
/******/ 						module.exports = factory();
/******/ 					}
/******/ 				};
/******/ 				startedInstallModules[id] = true;
/******/ 				var onError = (error) => {
/******/ 					delete installedModules[id];
/******/ 					__webpack_require__.m[id] = (module) => {
/******/ 						delete __webpack_require__.c[id];
/******/ 						throw error;
/******/ 					}
/******/ 				};
/******/ 				try {
/******/ 					var promise = moduleToHandlerMapping[id]();
/******/ 					if(promise.then) {
/******/ 						promises.push(installedModules[id] = promise.then(onFactory)['catch'](onError));
/******/ 					} else onFactory(promise);
/******/ 				} catch(e) { onError(e); }
/******/ 				}
/******/ 			});
/******/ 		}
/******/ 	}
/******/ })();
/******/ 
/******/ /* webpack/runtime/jsonp chunk loading */
/******/ (() => {
/******/ 	// no baseURI
/******/ 	
/******/ 	// object to store loaded and loading chunks
/******/ 	// undefined = chunk not loaded, null = chunk preloaded/prefetched
/******/ 	// [resolve, reject, Promise] = chunk loading, 0 = chunk loaded
/******/ 	var installedChunks = {
/******/ 		792: 0
/******/ 	};
/******/ 	
/******/ 	__webpack_require__.f.j = (chunkId, promises) => {
/******/ 			// JSONP chunk loading for javascript
/******/ 			var installedChunkData = __webpack_require__.o(installedChunks, chunkId) ? installedChunks[chunkId] : undefined;
/******/ 			if(installedChunkData !== 0) { // 0 means "already installed".
/******/ 	
/******/ 				// a Promise means "currently loading".
/******/ 				if(installedChunkData) {
/******/ 					promises.push(installedChunkData[2]);
/******/ 				} else {
/******/ 					if(true) { // all chunks have JS
/******/ 						// setup Promise in chunk cache
/******/ 						var promise = new Promise((resolve, reject) => (installedChunkData = installedChunks[chunkId] = [resolve, reject]));
/******/ 						promises.push(installedChunkData[2] = promise);
/******/ 	
/******/ 						// start chunk loading
/******/ 						var url = __webpack_require__.p + __webpack_require__.u(chunkId);
/******/ 						// create error before stack unwound to get useful stacktrace later
/******/ 						var error = new Error();
/******/ 						var loadingEnded = (event) => {
/******/ 							if(__webpack_require__.o(installedChunks, chunkId)) {
/******/ 								installedChunkData = installedChunks[chunkId];
/******/ 								if(installedChunkData !== 0) installedChunks[chunkId] = undefined;
/******/ 								if(installedChunkData) {
/******/ 									var errorType = event && (event.type === 'load' ? 'missing' : event.type);
/******/ 									var realSrc = event && event.target && event.target.src;
/******/ 									error.message = 'Loading chunk ' + chunkId + ' failed.\n(' + errorType + ': ' + realSrc + ')';
/******/ 									error.name = 'ChunkLoadError';
/******/ 									error.type = errorType;
/******/ 									error.request = realSrc;
/******/ 									installedChunkData[1](error);
/******/ 								}
/******/ 							}
/******/ 						};
/******/ 						__webpack_require__.l(url, loadingEnded, "chunk-" + chunkId, chunkId);
/******/ 					}
/******/ 				}
/******/ 			}
/******/ 	};
/******/ 	
/******/ 	// no prefetching
/******/ 	
/******/ 	// no preloaded
/******/ 	
/******/ 	// no HMR
/******/ 	
/******/ 	// no HMR manifest
/******/ 	
/******/ 	// no on chunks loaded
/******/ 	
/******/ 	// install a JSONP callback for chunk loading
/******/ 	var webpackJsonpCallback = (parentChunkLoadingFunction, data) => {
/******/ 		var [chunkIds, moreModules, runtime] = data;
/******/ 		// add "moreModules" to the modules object,
/******/ 		// then flag all "chunkIds" as loaded and fire callback
/******/ 		var moduleId, chunkId, i = 0;
/******/ 		if(chunkIds.some((id) => (installedChunks[id] !== 0))) {
/******/ 			for(moduleId in moreModules) {
/******/ 				if(__webpack_require__.o(moreModules, moduleId)) {
/******/ 					__webpack_require__.m[moduleId] = moreModules[moduleId];
/******/ 				}
/******/ 			}
/******/ 			if(runtime) var result = runtime(__webpack_require__);
/******/ 		}
/******/ 		if(parentChunkLoadingFunction) parentChunkLoadingFunction(data);
/******/ 		for(;i < chunkIds.length; i++) {
/******/ 			chunkId = chunkIds[i];
/******/ 			if(__webpack_require__.o(installedChunks, chunkId) && installedChunks[chunkId]) {
/******/ 				installedChunks[chunkId][0]();
/******/ 			}
/******/ 			installedChunks[chunkId] = 0;
/******/ 		}
/******/ 	
/******/ 	}
/******/ 	
/******/ 	var chunkLoadingGlobal = self["webpackChunkregimob_parcr_comcl_front"] = self["webpackChunkregimob_parcr_comcl_front"] || [];
/******/ 	chunkLoadingGlobal.forEach(webpackJsonpCallback.bind(null, 0));
/******/ 	chunkLoadingGlobal.push = webpackJsonpCallback.bind(null, chunkLoadingGlobal.push.bind(chunkLoadingGlobal));
/******/ })();
/******/ 
/************************************************************************/
/******/ 
/******/ // module cache are used so entry inlining is disabled
/******/ // startup
/******/ // Load entry module and return exports
/******/ var __webpack_exports__ = __webpack_require__(84429);
/******/ 
