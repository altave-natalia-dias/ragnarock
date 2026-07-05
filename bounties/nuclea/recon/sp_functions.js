// Hack para elementos de bloco HTML5 funcionarem no IE8
document.createElement('header');
document.createElement('nav');
document.createElement('section');
document.createElement('article');
document.createElement('aside');
document.createElement('footer');
document.createElement('hgroup');

function formatMoney(component, length) {
    var num = $("input:text[id=" + component.id + "]").val();
    num = num.replace(/[\D]+/g, '');
    if (num.length > 0 && num.length <= length) {
        num = num.replace(/([0-9]{2})$/g, ",$1");
        if (num.length > 6) {
            num = num.replace(/(\d)(?=(\d{3})+\,)/g, "$1.")
        }
        $("input:text[id=" + component.id + "]").val(num);
    } else {
        $("input:text[id=" + component.id + "]").val('');
    }
}

function filtroTabela(idInput, idTable) {
    // Declare variables
    var input, filter, table, tr, td, i, txtValue;
    input = document.getElementById(idInput);
    filter = input.value.toUpperCase();
    table = document.getElementById(idTable);
    tr = table.getElementsByTagName("tr");

    // Loop through all table rows, and hide those who don't match the search query
    for (i = 0; i < tr.length; i++) {
        td = tr[i].getElementsByTagName("td")[0];
        if (td) {
            txtValue = td.textContent || td.innerText;
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }
    }
}

function onlyNumbers(e)	// permite apenas valores numericos e CTRL+C / CTRL+V
{
    var tecla = Number();
    if (window.event) {
        tecla = e.keyCode;
    }
    else if (e.which) {
        tecla = e.which;
    }
    else {
        return true;
    }

    if (e.ctrlKey && (tecla == "67" || tecla == "99" || tecla == "86" || tecla == "118")) { // permite o uso de CTRL-C / CTRL-V
        window.event ? event.returnValue = false : event.preventDefault();
        return true;
    }

    if (((tecla >= "33") && (tecla <= "43")) || 	// bloqueia teclas abaixo de numéricos (vide tabela keycode para javascript)
        ((tecla >= "58") && (tecla <= "126")) ||	// bloqueia teclas acima de numéricos
        (tecla == "45") || (tecla == "46") ||   // bloqueia caracter '-' e '.'
        (tecla == "47") || (tecla > "127")		// bloqueia '/' e outros caracteres
    ) {
        return false;
    }
}

function AjustarIframe() {
    ResizeWH()
}
function uploadFileConsignatarioEnte(controle, tipodoc){
	$("#idTipDoc").val(tipodoc);
	$("#"+controle).click();
	
}
function ResizeWH() {
    var w;
    var h;
    w = document.getElementById("right").clientWidth;
    h = document.getElementById("right").clientHeight;
    parent.WHFRAME(w, h);
}


function liberaMargem() {
    document.getElementById('radioLiberaMargemSim').checked = false;
    document.getElementById('radioLiberaMargemNao').checked = false;
    if (document.getElementById('vlrAlterado').value == '') {
        document.getElementById('radioLiberaMargemSim').disabled = true;
        document.getElementById('radioLiberaMargemNao').disabled = true;
    } else {
        document.getElementById('radioLiberaMargemSim').disabled = false;
        document.getElementById('radioLiberaMargemNao').disabled = false;
    }
}

function mostrarEtapa2() {
    document.getElementById('divEtapa1').className = 'itemOculto';
    document.getElementById('divEtapa2').className = 'passosConteudo itemVisivel';
    document.getElementById('passoEtapa1').className = 'passo inativo';
    document.getElementById('passoEtapa2').className = 'passo ativo';
}

function mostrarEtapa1() {
    document.getElementById('divEtapa1').className = 'passosConteudo itemVisivel';
    document.getElementById('divEtapa2').className = 'itemOculto';
    document.getElementById('passoEtapa1').className = 'passo ativo';
    document.getElementById('passoEtapa2').className = 'passo inativo';
}


function esconderSecao(identificador, botaoRecolher, botaoExpandir) {


    document.getElementById(identificador).className = "itemOculto blocoDados2";
    //alert(botaoRecolher);
    document.getElementById(botaoRecolher).className = "itemOculto";
    //alert(botaoExpandir);

    //mostrar('btExpandirFiltro');

    //document.getElementById('btExpandirFiltro').className = "itemVisivel btExpandir";
}

function mostrarSecao(identificador) {
    var opcao = document.getElementById(identificador).className;
    document.getElementById(identificador).className = "itemVisivel blocoDados2";
    mostrar('btRecolherFiltro');
    esconder('btExpandirFiltro');
    document.getElementById('btRecolherFiltro').className = "itemVisivel btRecolher";
}


function OcultarExpandir(objetoDiv, imgBotao) {
    var secao = document.getElementById(objetoDiv).className;
    if ((secao).indexOf('itemVisivel') > -1) { //Visível
        document.getElementById(objetoDiv).className = secao.replace('itemVisivel', 'itemOculto');
        document.getElementById(imgBotao).className = "btExpandir";
    } else if ((secao).indexOf('itemOculto') > -1) { //Oculto
        document.getElementById(objetoDiv).className = secao.replace('itemOculto', 'itemVisivel');
        document.getElementById(imgBotao).className = "btRecolher";
    } else { //Caso que o desenvolvedor esqueceu de colocar o class 'itemVisivel'
        document.getElementById(objetoDiv).className = secao + ' itemOculto';
        document.getElementById(imgBotao).className = "btExpandir";
    }

}

function OcultarDIV(objetoDiv) {
    var secao = document.getElementById(objetoDiv).className;
    if ((secao).indexOf('itemVisivel') > -1) {
        document.getElementById(objetoDiv).className = secao.replace('itemVisivel', 'itemOculto');
    }
}

function mostrar(identificador) {
    var opcao = document.getElementById(identificador).className;
    document.getElementById(identificador).className = "itemVisivel";
}


function esconder(identificador) {
    var opcao = document.getElementById(identificador).className;
    document.getElementById(identificador).className = "itemOculto";
}

function esconderResultados() {
    document.getElementById('divResultados').className = "itemOculto";
    ;
}

function mostrarResultados() {
    document.getElementById('divResultados').className = "itemVisivel";
    ;
}


function OcultarExpandirTB(objetoDiv, imgBotao) {
    var secao = document.getElementById(objetoDiv).className;

    if (secao == "tbGrid") {
        document.getElementById(objetoDiv).className = "itemOculto";
        document.getElementById(imgBotao).className = "btExpandir";
    }
    else {
        document.getElementById(objetoDiv).className = "tbGrid";
        document.getElementById(imgBotao).className = "btRecolher";
    }

}


function mostrarPop(identificador) {
    var opcao = document.getElementById(identificador).className;
    document.getElementById(identificador).className = "popUp itemVisivel";

}


function esconderPop(identificador) {
    var opcao = document.getElementById(identificador).className;
    document.getElementById(identificador).className = "popUp itemOculto";
}

function esconderValores() {
    document.getElementById('divTextoValor').className = "itemOculto";
    document.getElementById('divTextoPercentual').className = "itemOculto";
    document.getElementById('divTextoValorDivisor').className = "itemOculto";
    document.getElementById('divTextoValorAntigo').className = "itemOculto";
    document.getElementById('divTextoValorNovo').className = "itemOculto";
    document.getElementById('divBtAdicionar').className = "itemOculto";
}

function tipoReajuste() {
    var valor = document.getElementById('cboTipoReajuste').value;
    // if (valor == "novoValor" || valor == "subtracao" || valor == "valorAdicional")
    // Usando ou para || não permitiu visulização em algumas máquinas

    if (valor == "novoValor") {
        esconderValores();
        document.getElementById('divTextoValor').className = "dados itemVisivel";
    }
    else if (valor == "subtracao") {
        esconderValores();
        document.getElementById('divTextoValor').className = "dados itemVisivel";
    }
    else if (valor == "valorAdicional") {
        esconderValores();
        document.getElementById('divTextoValor').className = "dados itemVisivel";
    }
    else if (valor == "percentual") {
        esconderValores();
        document.getElementById('divTextoPercentual').className = "dados itemVisivel";
    }

    else if (valor == "valorDivisor") {
        esconderValores();
        document.getElementById('divTextoValorDivisor').className = "dados itemVisivel";
    }


    else if (valor == "dePara") {
        esconderValores();
        document.getElementById('divTextoValorAntigo').className = "dados itemVisivel";
        document.getElementById('divTextoValorNovo').className = "dados itemVisivel";
        document.getElementById('divBtAdicionar').className = "dados itemVisivel";
    }

    else {
        //
    }

}

function definirEspecie() {
    var valor = document.getElementById('cboTipo').value;
    if (valor == "financeira") {
        document.getElementById('blocoEspecieFinanceira').className = "itemVisivel";
        document.getElementById('blocoEspecieNFinanceira').className = "itemOculto";
        document.getElementById('blocoDadosGerais').className = "itemVisivel";
        document.getElementById('botoesFinalizar').className = "botoes externos itemVisivel";
    }
    else if (valor == "naoFinanceira") {
        document.getElementById('blocoEspecieFinanceira').className = "itemOculto";
        document.getElementById('blocoEspecieNFinanceira').className = "itemVisivel";
        document.getElementById('blocoDadosGerais').className = "itemVisivel";
        document.getElementById('botoesFinalizar').className = "botoes externos itemVisivel";
    }
    else {
        alert("Selecione um tipo de espécie");
    }
}

function definirNivel() {
    var valor = document.getElementById('cboNivel').value;
    if (valor == "ente") {
        document.getElementById('divOrgao').className = "itemOculto";
    }
    else if (valor == "orgao") {
        document.getElementById('divOrgao').className = "dados itemVisivel";
    }
    else {
        alert("Selecione um nível hierárquico");
    }
}


function associarPerfil() {
    var valor = document.getElementById('cboPerfil').value;
    if (valor != "selecione") {
        document.getElementById('divBtAdicionar').className = "dados itemVisivel";
    }

    else {
        document.getElementById('divBtAdicionar').className = "itemOculto";
    }
}

/*
if (valor  == 'financeira' ){

	}
		else
		 (valor =='naofinanceira'){
		alert(10);


	}

}
*/

function playAudioCaptcha() {
    var canPlayWav = false;
    var audioTagSupport = !!(document.createElement('audio').canPlayType); // audio tag
    if (audioTagSupport) {
        audio = document.getElementById('audioCaptchaPlayer');
        if (audio.canPlayType) { // supports WAV?
            canPlayWav = ("no" != audio.canPlayType("audio/wav")) && ("" != audio.canPlayType("audio/wav"));
        }
    }
    if (canPlayWav) {
        audio.load();
        audio.play();
    } else {
        var player = document.getElementById('divAudioPlayer'); // embed tag
        player.innerHTML = "<embed src='cipAudio' autostart='true' loop='false' type='audio/wav' hidden='true' volume='100' />";
    }
    document.getElementById('captcha').focus();
}

function redimensionar(de, para, menos) {
    $("#" + para).width($("#" + de).width() - menos);
}

function testLength(campo, tamanhoMax) {
    if (campo.value.length > tamanhoMax) {
        campo.value = campo.value.substring(0, tamanhoMax);
    }
}

function habilitarInputPorRadioButton(inputRadio, inputHabilitar) {

    if (document.getElementById(inputRadio).checked) {
        document.getElementById(inputHabilitar).disabled = false;
    } else {
        document.getElementById(inputHabilitar).disabled = true;
        document.getElementById(inputHabilitar).value = "";
    }
}

function SomenteNumero(obj, e) {
    var tecla = (window.event) ? e.keyCode : e.which;
    if (tecla == 8 || tecla == 0)
        return true;
    if (tecla != 44 && tecla < 48 || tecla > 57)
        return false;
}

function preencherConsignatario(origem, destino) {

    origem = document.getElementById(origem);
    destino = document.getElementById(destino);

    if (origem.nodeName == "SELECT") {

        if (origem.selectedIndex > 0) {
            destino.value = getNumConsigEnteDaComboConsignatario(origem[origem.selectedIndex].text);
        } else {
            destino.value = "";
        }

    } else if (origem.nodeName == "INPUT") {

        destino.selectedIndex = 0;
        for (i = 0; i < destino.options.length; i++) {
            numConsigEnte = getNumConsigEnteDaComboConsignatario(destino.options[i].text);

            if (numConsigEnte === origem.value) {
                destino.selectedIndex = i;
                if ("createEvent" in document) {
                    var evt = document.createEvent("HTMLEvents");
                    evt.initEvent("change", false, true);
                    destino.dispatchEvent(evt);
                }
                else
                    destino.fireEvent("onchange");
                break;
            }
        }
    }
}

function getNumConsigEnteDaComboConsignatario (valor) {
    for (l = valor.length - 1; l >= 0; l--) {
        var index = l;
        if (valor.charAt(index) == "-") {
            if (valor.charAt(index - 1) == " ") {
                return valor.substring(l+2 ,valor.length);

            } else {
                for (k = l; k >= 0; k--) {
                    if (valor.charAt(k) == " "){
                        return valor.substring(k+1 ,l);

                    }
                }
            }
        }
    }
}

/*
function atualizarPaginacaoAlternativa() {

	if (document.getElementById("divResultados").style.display != "none") {

		//  formAction = document.getElementById("formConsultaAverbacaoPage").action;
		//  pageId = formAction.substring(formAction.indexOf("?") + 1, formAction.indexOf("."));
        //
		//  labelQuantRegistros = document.getElementById("labelTituloResultados").innerHTML;
		//  quantRegistros = labelQuantRegistros.substring(labelQuantRegistros.indexOf(" - ") + 3, labelQuantRegistros.indexOf(" registro"));
		//  quantPaginas = Math.ceil(quantRegistros / 50);
		//  quantPaginas = quantPaginas > 10 ? 10 : quantPaginas;
        //
		//  paginas = document.getElementsByClassName("goto");
		//  for (i = 0; i < paginas.length; i++) {
		//  	if (paginas[i].innerHTML.indexOf("href") == -1) {
		//  		paginaAtual = paginas[i].innerHTML.substring(paginas[i].innerHTML.indexOf("<span>") + 6, paginas[i].innerHTML.indexOf("</span>"));
		//  		break;
		//  	}
		//  }
        //
		//  if (paginaAtual == 1) {
		//  	links = "<span class=\"goto\"><span>&lt;&lt;</span></span>";
		//  	links += " <span class=\"goto\"><span>&lt;</span></span>";
		//  } else {
		//  	links = "<span class=\"goto\"><a href=\"./consultar?" + pageId + ".ILinkListener-form-divResultados-divPaginacao-navegacao-first\"><span>&lt;&lt;</span></a></span>";
		//  	links += " <span class=\"goto\"><a href=\"./consultar?" + pageId + ".ILinkListener-form-divResultados-divPaginacao-navegacao-navigation-" + (paginaAtual - 2) + "-pageLink\"><span>&lt;</span></a></span>";
		//  }
        //
		//  for (i = 0; i < quantPaginas; i++) {
		//  	if (paginaAtual == i + 1) {
		//  		links += " <span class=\"goto\"><span>" + (i + 1)  + "</span></span>";
		//  	} else {
		//  		links += " <span class=\"goto\"><a href=\"./consultar?" + pageId + ".ILinkListener-form-divResultados-divPaginacao-navegacao-navigation-" + i + "-pageLink\"><span>" + (i + 1)  + "</span></a></span>";
		//  	}
		//  }
        //
		//  if (paginaAtual == quantPaginas) {
		//  	links += " <span class=\"goto\"><span>&gt;</span></span>";
		//  	links += " <span class=\"goto\"><span>&gt;&gt;</span></span>";
		//  } else {
		//  	links += " <span class=\"goto\"><a href=\"./consultar?" + pageId + ".ILinkListener-form-divResultados-divPaginacao-navegacao-navigation-" + (paginaAtual) + "-pageLink\"><span>&gt;</span></a></span>";
		//  	links += " <span class=\"goto\"><a href=\"./consultar?" + pageId + ".ILinkListener-form-divResultados-divPaginacao-navegacao-navigation-" + (quantPaginas - 1) + "-pageLink\"><span>&gt;&gt;</span></a></span>";
		//  }
        //
		//  document.getElementById("divPaginacaoAlternativa").innerHTML = links;
		//  document.getElementById("divPaginacao").style.visibility = "hidden";

		paginas = document.getElementsByClassName("goto");
		for (i = 0; i < paginas.length; i++) {
			paginaAtual = paginas[i].innerHTML.substring(paginas[i].innerHTML.indexOf("<span>") + 6, paginas[i].innerHTML.indexOf("</span>"));
			if (i == 0) primeiraPagina = paginaAtual;
			if (paginaAtual > 10) paginas[i].style.display = "none";
		}

		if (primeiraPagina == 1) {
			paginas = document.getElementsByClassName("first");
			for (i = 0; i < paginas.length; i++) {
				paginas[i].style.display = "none";
			}

			paginas = document.getElementsByClassName("prev");
			for (i = 0; i < paginas.length; i++) {
				paginas[i].style.display = "none";
			}
		}

		paginas = document.getElementsByClassName("next");
		for (i = 0; i < paginas.length; i++) {
			paginas[i].style.display = "none";
		}

		paginas = document.getElementsByClassName("last");
		for (i = 0; i < paginas.length; i++) {
			paginas[i].style.display = "none";
		}
	}
}
*/

// Limitador textarea justificativa para limitar no IE 8 e 9
function limitadorJustificativa(field, maxlimit) {
    if (field.value.length > maxlimit) {
        field.value = field.value.substring(0, maxlimit);
        return false;
    }
}

function limparRadios(radioButton) {

    radios = document.getElementsByTagName("input");

    for (i = 0; i < radios.length; i++) {
        if (radios[i].name.indexOf("rdSelecionar") > 0 && radios[i].name != radioButton.name) {
            radios[i].checked = false;
        }
    }
}

function selecionarTodos(checked, inputPrefix) {

    checkboxes = document.getElementsByTagName("input");

    for (i = 0; i < checkboxes.length; i++) {
        if (checkboxes[i].name.indexOf(inputPrefix) == 0 && !checkboxes[i].disabled) {
            checkboxes[i].checked = checked;
        }
    }
}

function selecionarTodosAutorizacao(checked, inputPrefix) {

    checkboxes = document.getElementsByTagName("input");

    for (i = 0; i < checkboxes.length; i++) {
        if (checkboxes[i].name.indexOf(inputPrefix) != -1 && !checkboxes[i].disabled) {
            checkboxes[i].checked = checked;
        }
    }
}
function checkMobile(){
   var isMobile = navigator.userAgent.toLowerCase().match(/mobile/i);
   if (isMobile){
	  $("#guias").remove();
	  $(".guiasConteudo").remove();
	  $("#divMsgMobile").show();
   }
}	
function validarSelecionarTodos(checkAllId, inputPrefix) {

    var isAllChecked = true;

    checkboxes = document.getElementsByTagName("input");

    for (i = 0; i < checkboxes.length; i++) {
        if (checkboxes[i].name.indexOf(inputPrefix) == 0 && !checkboxes[i].checked) {
            isAllChecked = false;
            break;
        }
    }

    document.getElementById(checkAllId).checked = isAllChecked;
}
         
function downloadSelected(id){
	debugger;
	var base =  window.location.href;
	var find =  '-1.ILinkListener-form-' + id ;
	if (base.indexOf(find) > -1 ){
		base = base.substring(0, base.indexOf(find) + find.length);
	}
 	window.location.href = base + find + '&t=' +  (new Date()).getTime();
	return false;
} 

(function ($) {

        jQuery.keepAlive = function (options) {

            var defaults = {
                keepAliveUrl: '/keepAlive',
                keepAliveAjaxRequestType: 'POST',
                keepAliveAfter: 1200000,
                appendTime: true
            };

            var o = defaults;

            var interval = null;

            if (options) {
                o = $.extend(defaults, options);
            }

            interval = setInterval(sendKeepAlive, o.keepAliveAfter);

            function sendKeepAlive() {

                $.ajax({
                    url: o.appendTime ? updateQueryStringParameter(o.keepAliveUrl, "_", new Date().getTime()) : o.keepAliveUrl,
                    type: o.keepAliveAjaxRequestType,
                    error: function () {
                        clearInterval(interval);
                    }
                });
            }

            function updateQueryStringParameter(uri, key, value) {
                var re = new RegExp("([?|&])" + key + "=.*?(&|#|$)", "i");

                if (uri.match(re)) {
                    return uri.replace(re, '$1' + key + "=" + value + '$2');
                } else {
                    var hash = '';

                    if (uri.indexOf('#') !== -1) {
                        hash = uri.replace(/.*#/, '#');
                        uri = uri.replace(/#.*/, '');
                    }

                    var separator = uri.indexOf('?') !== -1 ? "&" : "?";
                    return uri + separator + key + "=" + value + hash;
                }
            }

        };

    }
)(jQuery);

	
