(function(PFNConfig){
	var	root = '/gfe-pesquisamercado',
		ts = +Date.now();
	
	PFNConfig.config({
		appName: 'PesquisaMercadoModule',
		jsFiles: [
			root+'/v1/spas/pesquisa-api-module-min.js?_t='+ts,
			root+'/v1/spas/pesquisa-service-min.js?_t='+ts,
			root+'/v1/spas/pesquisaMercado/pesquisa-mercado-controller-min.js?_t='+ts,
			root+'/v1/spas/pesquisaMercado/demanda-detalhada-controller-min.js?_t='+ts,
			root+'/v1/spas/pesquisaMercado/questionamentos-controller-min.js?_t='+ts,
			root+'/v1/spas/pesquisaMercado/questionamentos/questionamentos-feitos-controller-min.js?_t='+ts,
			root+'/v1/spas/pesquisaMercado/questionamentos/novos-questionamentos-controller-min.js?_t='+ts,
			root+'/v1/spas/precificacao/precificacao-controller-min.js?_t='+ts,
			root+'/v1/spas/relatorioRequisitos/relatorio-requisitos-controller-min.js?_t='+ts,
			root+'/v1/spas/pesquisaMercado/todas-pesquisas-mercado-controller-min.js?_t='+ts,
			root+'/v1/spas/termosGerais/termos-gerais-controller-min.js?_t='+ts
		]
	});
	
	PFNConfig.config({
		appName: 'PesquisaMercadoApp',
		jsFiles: [
			root+'/v1/spas/pesquisa-mercado-app-min.js?_t='+ts
		]
	});
})(PFNConfig);