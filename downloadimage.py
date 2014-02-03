import argparse
from argparse import ArgumentTypeError
from downloadmanifest import DownloadManifest
import os
import subprocess

class DownloadParts(object):
    def __init__(self, **kwargs):
        parser = argparse.ArgumentParser(description=
                                         "Download parts from manifest")
        parser.add_argument('-m', '--manifest', dest='manifest', required=True,
                help='''Path to local 'download-manfiest''')
        parser.add_argument('-d', '--dest',dest='destination', required=True,
                help='''Destination path to write image to.
                Use '-' for stdout''')
        parser.add_argument('-x', '--xsd',dest='xsd', default=None,
                help='''Local Path to 'download-manifest xsd used
                to validate manfiest xml''')
        parser.add_argument('-k', '--privatekey', metavar='FILE',
                help='''File containing the private key to decrypt the bundle
                with.  This must match the certificate used when bundling the
                image.''')
        parser.add_argument('-e', '--enc-key', dest='enc_key',
                help='''Key used to decrypt bundled image'''),
        parser.add_argument('-v', '--enc-iv', dest='enc_iv',
                help='''Initialization vector used to decrypt bundled image'''),

        self.args = parser.parse_args()
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

        #Get Mandatory manifest...
        manifest = self.args.get('manifest')
        if manifest:
            if not isinstance(manifest, DownloadManifest):
                #Read manifest file into manifest obj...
                manifest_path = os.path.expanduser(os.path.abspath(
                    self.args['manifest']))
                if not os.path.exists(manifest_path):
                    raise ArgumentTypeError("Manifest '{0}' does not exist"
                                        .format(self.args['manifest']))
                if not os.path.isfile(manifest_path):
                    raise ArgumentTypeError("Manifest '{0}' is not a file"
                                        .format(self.args['manifest']))
                #Read manifest into BundleManifest obj...
                self.args['manifest'] = DownloadManifest.read_from_file(manifest_path,
                                                                        xsd_file)
        else:
            raise argparse.ArgumentError(None, 'Manifest is required (-m)')


    def _download_parts_to_fileobj(self, manifest, dest_fileobj):
        for part in manifest.image_parts:
            part.download(dest_fileobj=dest_fileobj)

    def _download_to_unbundlestream(self,manifest, dest_fileobj):

        openssl = subprocess.Popen(['euca-unbundlestream', 'enc', '-d', '-aes-128-cbc',
                                    '-K', enc_key, '-iv', enc_iv],
                                   stdin=infile, stdout=subprocess.PIPE,
                                   close_fds=True, bufsize=-1)
        euca2ools.bundle.util.waitpid_in_thread(openssl.pid, 'openssl', debug=debug)


    def main(self):
        self.configure()
        manifest = self.args.get('manifest')
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