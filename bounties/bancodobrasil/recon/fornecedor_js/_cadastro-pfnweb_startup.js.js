(function(PFNConfig) {
	var root = '/cadastro-pfnweb',
		ts = +Date.now();

	PFNConfig.config({
		appName: 'CadastroFornecedorModule',
		jsFiles: [
			root + '/v1/spas/scripts/utils-min.js?_t=' + ts,
			root + '/v1/spas/cadastro-api-module-min.js?_t=' + ts,			
			root + '/v1/spas/dossieDigital/dossie-digital-auxiliar-service-min.js?_t=' + ts,
			root + '/v1/spas/cadastro-service-min.js?_t=' + ts,
			root + '/v1/spas/cadastro/cadastro-fornecedor-controller-min.js?_t=' + ts,
			root + '/v1/spas/cadastro/dados-complementares-fornecedor-controller-min.js?_t=' + ts,
			root + '/v1/spas/cadastro/lista-fornecedores-controller-min.js?_t=' + ts,
			root + '/v1/spas/regiaoAtendimento/regiao-atendimento-controller-min.js?_t=' + ts,
			root + '/v1/spas/regiaoAtendimento/regiao-atendimento-constantes-min.js?_t=' + ts,
			root + '/v1/spas/linhaFornecimento/linha-fornecimento-controller-min.js?_t=' + ts,
			root + '/v1/spas/linhaFornecimento/linha-fornecimento-constantes-min.js?_t=' + ts,
			root + '/v1/spas/solucaoCognitiva/solucao-cognitiva-service-min.js?_t=' + ts,
			root + '/v1/spas/solucaoCognitiva/solucao-cognitiva-controller-min.js?_t=' + ts,
			root + '/v1/spas/scripts/directives-utils-min.js?_t=' + ts,
			root + '/v1/spas/dossieDigital/dossie-digital-controller-min.js?_t=' + ts,
			root + '/v1/spas/scripts/filters-utils-min.js?_t=' + ts,
			root + '/v1/spas/dossieFornecedor/dossie-fornecedor-controller-min.js?_t=' + ts
		]
	});

	PFNConfig.config({
		appName: 'CadastroFrnApp',
		jsFiles: [
			root + '/v1/spas/cadastro-frn-app-min.js?_t=' + ts
		]
	});
})(PFNConfig);