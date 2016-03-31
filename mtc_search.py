__author__ = 'javier'

from apps.administrador.models import CONDUCTORES
from apps.administrador.models import PersonalTercero
from bs4 import BeautifulSoup
from datetime import datetime
from django.conf import settings

import urllib2
import requests
import os
import csv


class SLCPMTC(object):
    _url = u'http://slcp.mtc.gob.pe/'
    _tmp_dir = None
    _debug = True

    _current_viewstate_token = None
    _current_eventvalidation_token = None

    def __init__(self, *args, **kwargs):
        self._url = settings.SLCP_MTC_URL
        self._ok = True
        self._code = None
        self._debug = kwargs.get('debug', False)
        self._tmp_dir = os.path.join(settings.BASE_DIR, "util/SLCP_MTC_SEARCH/tmp")

    def init(self):
        try:
            html = self.parse_web_page()
            if html is not None:
                self.set_tokens(html)
                if self._debug:
                    current_date = datetime.now()
                    file_name = u'slcp_mtc_gob_pe_{0}.txt'.format(current_date)
                    file_path = os.path.join(self._tmp_dir, file_name)
                    with open(file_path, 'w') as f:
                        f.write(str(html))
                return self.prepare_manual_tokens()
        except Exception as e:
            print 'SLCPMTC|init', e

        return False


    def search(self, license):
        license = license.strip()
        try:
            data = self.get_data_search_by_license(license)
            headers = self.get_headers()
            response = requests.post(self._url, data=data, headers=headers)
            data = SLCPMTC.parse_search_result(response, license)
            return data
        except Exception as e:
            print 'SLCPMTC|search', e
            data = {'status': 'ERROR', 'licencia': license, 'error': True, 'msg_error': 'Error mandando peticion de consulta'}
            return data

    @staticmethod
    def parse_search_result(response, license):
        data = {'status': 'FOUND', 'licencia': license, 'error': False, 'msg_error': ''}
        if response.ok:
            html_object = BeautifulSoup(response.text, 'lxml')
            if html_object:
                div_exists = html_object.find('div', {'id': 'PnlMensajeNoExisteas'})
                if div_exists is not None:
                    data['status'] = 'NOT_FOUND'
                else:
                    data = SLCPMTC.load_search_result(html_object, data)
                return data
            else:
                data = {'status': 'ERROR', 'licencia': license, 'error': True, 'msg_error': 'Error parseando resultado'}
                return data
        else:
            data = {'status': 'ERROR', 'licencia': license, 'error': True, 'msg_error': 'Error en autenticacion de tokens y parametros'}
            return data

    @staticmethod
    def load_search_result(html_object, data):

        nombre = html_object.find('span', {'id': 'lblAdministrado'})
        documento = html_object.find('span', {'id': 'lblDni'})
        licencia = html_object.find('span', {'id': 'lblLicencia'})
        categoria = html_object.find('span', {'id': 'lblClaseCategoria'})
        vigencia = html_object.find('span', {'id': 'lblVigencia'})
        estado = html_object.find('span', {'id': 'lblEstadoLicencia'})

        if nombre is not None:
            data['nombre'] = nombre.text.encode('utf-8')

        if documento is not None:
            data['documento'] = documento.text.encode('utf-8')

        if licencia is not None:
            data['licencia'] = licencia.text.encode('utf-8')

        if categoria is not None:
            data['categoria'] = categoria.text.encode('utf-8')

        if vigencia is not None:
            data['vigencia'] = vigencia.text.encode('utf-8')

        if estado is not None:
            data['estado'] = estado.text.encode('utf-8')

        return data

    def prepare_manual_tokens(self):
        try:
            data = self.get_data_change_search_type()
            headers = self.get_headers()
            response = requests.post(self._url, data=data, headers=headers)
            if response.ok:
                result_text = response.text
                if self._debug:
                    current_date = datetime.now()
                    file_name = u'slcp_mtc_gob_pe_II_{0}.txt'.format(current_date)
                    file_path = os.path.join(self._tmp_dir, file_name)
                    with open(file_path, 'w') as f:
                        f.write(str(result_text))
                return self.reload_manual_tokens(result_text)
            else:
                self._ok = False
                self._code = u'500'
                return False
        except Exception as e:
            print 'SLCPMTC|prepare_manual_tokens', e
            return False

    def reload_manual_tokens(self, result_text):
        if result_text:
            tmp_str_viewsstate = '__VIEWSTATE'
            tmp_str_eventvalidation = '__EVENTVALIDATION'
            tmp_start_index_viewstate = result_text.find('__VIEWSTATE')
            tmp_start_index_eventvalidation = result_text.find('__EVENTVALIDATION')

            if tmp_start_index_eventvalidation > 0 and tmp_start_index_viewstate  > 0:
                tmp_start_index_viewstate += (len(tmp_str_viewsstate) + 1)
                tmp_end_index_viewstate = result_text.find('|', tmp_start_index_viewstate)
                self._current_viewstate_token = result_text[tmp_start_index_viewstate:tmp_end_index_viewstate]

                tmp_start_index_eventvalidation += (len(tmp_str_eventvalidation) + 1)
                tmp_end_index_eventvalidation = result_text.find('|', tmp_start_index_eventvalidation)
                self._current_eventvalidation_token = result_text[tmp_start_index_eventvalidation:tmp_end_index_eventvalidation]

                return True
            else:
                return False
        else:
            return False

    def parse_web_page(self):
        try:
            respuesta = urllib2.urlopen(self._url)
            data = respuesta.read()
            html_object = BeautifulSoup(data, 'lxml')
            return html_object
        except Exception, e:
            print 'SLCPMTC|parse_web_page', e
            return None

    def set_tokens(self, html):
        try:
            if html is not None:
                element = html.find('input', {'id': '__VIEWSTATE', 'type': 'hidden'})
                if element:
                    self._current_viewstate_token = element.get('value', None)

                element = html.find('input', {'id': '__EVENTVALIDATION', 'type': 'hidden'})
                if element:
                    self._current_eventvalidation_token = element.get('value', None)
        except Exception, e:
            print 'SLCPMTC|set_tokens', e

    def get_headers(self):
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'es-419,es;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            # 'Cookie':'_ga=GA1.3.81006674.1452990760',
            # 'Content-Length':'3934',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Host': 'slcp.mtc.gob.pe',
            'Origin': 'http://slcp.mtc.gob.pe',
            'Referer': 'http://slcp.mtc.gob.pe/',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.75 Safari/537.36',
            'X-MicrosoftAjax': 'Delta=true',
            'X-Requested-With': 'XMLHttpRequest'
        }

    def get_data_change_search_type(self):
        return {
            'ScriptManager': 'UpdatePanel|rbtnlBuqueda$1',
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'rbtnlBuqueda$1',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': self._current_viewstate_token,
            '__VIEWSTATEENCRYPTED': '',
            '__EVENTVALIDATION': self._current_eventvalidation_token,
            'rbtnlBuqueda': '1',
            'ddlTipoDocumento': '2',
            'txtNroDocumento': '',
            'hdCodAdministrado': '',
            'hdNumTipoDoc': '',
            'hdNumDocumento': '',
            'txtNroResolucion': '',
            'txtFechaResolucion': '',
            'txtIniSancion': '',
            'txtFinSancion': '',
            '__ASYNCPOST': True
        }

    def get_data_search_by_license(self, license):
        return {
            'ScriptManager': 'UpdatePanel|ibtnBusqNroLic',
            'rbtnlBuqueda': '1',
            'txtNroLicencia': license,
            # 'hdCodAdministrado':'1550531',
            'hdNumTipoDoc': '2',
            'hdNumDocumento': license[1:],
            'txtNroResolucion': '',
            'txtFechaResolucion': '',
            'txtIniSancion': '',
            'txtFinSancion': '',
            '__EVENTTARGET': 'ibtnBusqNroLic',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATE': self._current_viewstate_token,
            '__EVENTVALIDATION': self._current_eventvalidation_token,
            '__VIEWSTATEENCRYPTED': '',
            '__ASYNCPOST': True
        }


def verficiar_choferes():
    personal_tercero_list = PersonalTercero.objects.filter(tipo=CONDUCTORES)

    with open('/home/juan/Escritorio/choferes.csv', 'wb') as csvfile:
        archivo = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        archivo.writerow(['STATUS', 'LICENCIA', 'DOCUMENTO', 'CATEGORIA', 'VIGENCIA', 'ESTADO'])
        parser = SLCPMTC()
        if parser.init():
            for chofer in personal_tercero_list:
                licencia = chofer.nro_licencia
                data = parser.search(licencia)
                if data['status'] == 'ERROR':
                    archivo.writerow([data['status'], data['licencia'], '','', '', '', ''])
                elif data['status'] == 'NOT_FOUND':
                    archivo.writerow([data['status'], data['licencia'], '','', '', '', ''])
                elif data['status'] == 'FOUND':
                    if 'estado' in data:
                        archivo.writerow([data['status'], data['licencia'], data['nombre'], data['documento'], data['categoria'],
                                          data['vigencia'], data['estado']])
                    else:
                        archivo.writerow(['MULTIPLE', data['licencia'], '','', '', '', ''])
        else:
            print 'INIT'


def verficiar_choferes_archivo():
    archivo = '/home/juan/Escritorio/choferes.csv'
    data = csv.reader(open(archivo), delimiter=',', quotechar='"')
    with open('/home/juan/Escritorio/choferes_resultado.csv', 'wb') as csvfile:
        archivo = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        archivo.writerow(['STATUS', 'LICENCIA', 'DOCUMENTO', 'CATEGORIA', 'VIGENCIA', 'ESTADO'])
        parser = SLCPMTC()
        if parser.init():
            for row in data:
                licencia = row[0]
                print 'LICENCIA A BUSCAR --->', licencia
                data = parser.search(licencia)
                if data['status'] == 'ERROR':
                    archivo.writerow([data['status'], data['licencia'], '','', '', '', ''])
                elif data['status'] == 'NOT_FOUND':
                    archivo.writerow([data['status'], data['licencia'], '','', '', '', ''])
                elif data['status'] == 'FOUND':
                    if 'estado' in data:
                        archivo.writerow([data['status'], data['licencia'], data['nombre'], data['documento'], data['categoria'],
                                          data['vigencia'], data['estado']])
                    else:
                        archivo.writerow(['MULTIPLE', data['licencia'], '','', '', '', ''])
        else:
            print 'INIT FAILED'
