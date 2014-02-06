import argparse
from argparse import ArgumentTypeError
from urlparse import urlparse
import os
import threading
import subprocess
import traceback
from downloadmanifest import DownloadManifest


class DownloadParts(object):
    def __init__(self, **kwargs):
        parser = argparse.ArgumentParser(description=
                                         "Download parts from manifest")
        parser.add_argument('-m', '--manifest', dest='manifest', required=True,
                help='''Path to 'download-manifest. Use '-' to read manifest
                from stdin''')
        parser.add_argument('-d', '--dest',dest='destination', required=True,
                help='''Destination path to write image to.
                Use '-' for stdout.''')
        parser.add_argument('-x', '--xsd',dest='xsd', default=None,
                help='''Path to 'download-manifest xsd used
                to validate manfiest xml.''')
        parser.add_argument('--toolspath', dest='toolspath',default=None,
                help='''Local path to euca2ools.''')
        parser.add_argument('--maxbytes', dest='maxbytes', default=0,
                help='''Maximum bytes allowed to be written to the
                        destination.''')
        parser.add_argument('--debug', dest='debug', default=False,
                action='store_true', help='''Enable debug output''')
        self.args = parser.parse_args()
        self.debug = self.args.get('debug')
        self.configure()

    def configure(self):
        #Get optional destination directory...
        dest_file = self.args['destination']
        if not isinstance(dest_file, file) and not (dest_file == "-"):
            dest_file = os.path.expanduser(os.path.abspath(dest_file))
            self.args['destination'] = dest_file

        xsd_file = self.args.get('xsd', None)
        if xsd_file:
            if not isinstance(xsd_file, file):
                xsd_file = os.path.expanduser(os.path.abspath(xsd_file))
                self.args['xsd'] = xsd_file
        self._get_download_manifest_obj()

    def _get_download_manifest_obj(self):
        #Create DownloadManifest obj from the manifest argument...
        manifest = self.args.get('manifest')
        xsd_file = self.args.get('xsd', None)
        manifest_url = None
        if manifest:
            if isinstance(manifest, DownloadManifest):
                return
            if manifest == '-':
                #Manifest is being piped through stdin...
                fileobj = os.fdopen(os.dup(os.sys.stdin.fileno()))
                with fileobj:
                    self.args['manifest'] = DownloadManifest._read_from_fileobj(
                                            manifest_fileobj=fileobj,
                                            xsd=xsd_file)
                return

            #see if manifest is a url or local path
            try:
                parsed_url = urlparse(str(manifest))
            except:
                self.log.debug('Error parsing manifest argument as url,'
                               'trying local path')
                if self.debug:
                    traceback.print_exc()

            if not parsed_url or not parsed_url.scheme:
                #Read local manifest file into manifest obj...
                manifest_path = os.path.expanduser(os.path.abspath(
                    self.args['manifest']))
                if not os.path.exists(manifest_path):
                    raise ArgumentTypeError("Manifest '{0}' does not exist"
                                        .format(self.args['manifest']))
                if not os.path.isfile(manifest_path):
                    raise ArgumentTypeError("Manifest '{0}' is not a file"
                                        .format(self.args['manifest']))
                #Read manifest into BundleManifest obj...
                self.args['manifest'] = DownloadManifest.read_from_file(
                                        manifest_path, xsd_file)
                return
            else:
                #For now limit urls to http(s)...
                if not parsed_url.scheme in ['http', 'https']:
                    raise ArgumentTypeError('Manifest url only supports '
                                            'http, https at this time')
                self.args['manifest'] = DownloadManifest.read_from_url(
                                        manifest_url=str(manifest),
                                        xsd= xsd_file)
                return
        else:
            raise argparse.ArgumentError(None, 'Manifest is required (-m)')

    @classmethod
    def _open_pipe_fileobjs(cls):
        pipe_r, pipe_w = os.pipe()
        return os.fdopen(pipe_r), os.fdopen(pipe_w, 'w')

    def _download_parts_to_fileobj(self, manifest, dest_fileobj):
        for part in manifest.image_parts:
            part.download(dest_fileobj=dest_fileobj)

    def _download_to_unbundlestream(self,
                                    manifest,
                                    tools_path=None):
        if tools_path is None:
            tools_path = self.args.get('toolspath') or ""
        unbundle_tool_path = tools_path+'euca-unbundlestream'

        unbundle_ps = subprocess.Popen([unbundle_tool_path,
                                       '-e', manifest.enc_key,
                                       '-v', manifest.enc_iv,
                                       '-d', self.args.get('destination'),
                                       '--maxbytes', self.args.get('maxbytes'),
                                       '--debug', self.args.get('debug')])
        if unbundle_ps:
            pid_thread = threading.Thread(target=os.waitpid,
                                          args=(unbundle_ps.pid, 0))
            pid_thread.daemon = True
            pid_thread.start()
        download_r, download_w = self._open_pipe_fileobjs()
        unbundle_ps.stdin = download_r
        self._download_parts_to_fileobj(manifest=manifest,
                                        dest_fileobj=download_w)
        download_r.close()
        download_w.close()

    def main(self):
        self.configure()
        manifest =
        dest_file = self.args.get('destination')
        if isinstance(dest_file, file):
            dest_file_name = dest_file.name
        elif dest_file == "-":
            dest_file_name = '<stdout>'
            dest_file = os.fdopen(os.dup(os.sys.stdout.fileno()), 'w')
        else:
            dest_file_name = str(dest_file)
            dest_file = open(dest_file, 'w')

        with dest_file:
            if manifest.file_format == 'BUNDLE':
                self._download_to_unbundlestream(manifest=manifest,
                                                 dest_fileobj=dest_file)
            else:
                self._download_parts_to_fileobj(manifest=manifest, dest_fileobj=dest_file)






if __name__ == '__main__':
    DownloadParts.run()