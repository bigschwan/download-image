import logging
import lxml.etree
import lxml.objectify
import requests
from io import BytesIO
from downloadpart import DownloadPart


class DownloadManifest(object):
    def __init__(self, loglevel=None):
        self.log = logging.getLogger(self.__class__.__name__)
        if loglevel is not None:
            self.log.level = loglevel
        self.version = None
        self.file_format = None
        self.enc_key = None
        self.enc_iv = None
        self.image_size = None
        self.part_count = None
        self.image_parts = []
        self.signature = None
        self.signature_algorithm = None

    @classmethod
    def _validate_manifest(cls, manifest_fileobj, xsd_fileobj):
        xsd_doc = lxml.etree.parse(xsd_fileobj)
        xsd_schema = lxml.etree.XMLSchema(xsd_doc)
        xml_doc = lxml.etree.parse(manifest_fileobj)
        xsd_schema.assertValid(xml_doc)

    @classmethod
    def read_from_file(cls, manifest_path, xsd=None):
        xsd_fileobj = None
        if xsd:
            if not isinstance(xsd, file):
                xsd = open(xsd)
        try:
            manifest_fileobj = open(manifest_path)
            return cls._read_from_fileobj(manifest_fileobj, xsd=xsd)
        finally:
            if xsd_fileobj:
                xsd_fileobj.close()
            if manifest_fileobj:
                manifest_fileobj.close()

    @classmethod
    def read_from_url(cls, manifest_url, chunk_size=8192, xsd=None):
        fileobj = BytesIO()
        r = requests.get(manifest_url, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size):
            fileobj.write(chunk)
        fileobj.flush()
        fileobj.seek(0)
        return cls._read_from_fileobj(manifest_fileobj=fileobj, xsd=xsd)

    @classmethod
    def _read_from_fileobj(cls, manifest_fileobj, xsd=None):
        if xsd is not None:
            cls._validate_manifest(manifest_fileobj, xsd)
        #manifest_fileobj.seek(0)
        xml = lxml.objectify.parse(manifest_fileobj).getroot()
        manifest = cls()
        manifest.version = xml.version
        manifest.file_format = str(xml.__getattr__('file-format')).strip()
        manifest.enc_key = xml.bundle.__getattr__('encrypted-key')
        manifest.enc_iv = xml.bundle.__getattr__('encrypted-iv')
        manifest.image_size = long(xml.image.size)
        partcount = xml.image.parts.get('count')
        manifest.signature = xml.signature
        manifest.signature_algorithm = xml.signature.get('algorithm')
        for part in xml.image.parts.iter(tag='part'):
            manifest.image_parts.append(None)
        for xml_part in xml.image.parts.iter(tag='part'):
            part_index = int(xml_part.get('index'))
            byte_range = xml_part.__getattr__('byte-range')
            bytes_start = byte_range.get('start')
            bytes_end = byte_range.get('end')
            get_url = xml_part.__getattr__('get-url')
            manifest.image_parts[part_index] = DownloadPart(
                get_url=get_url,
                part_index=part_index,
                bytes_start=bytes_start,
                bytes_end=bytes_end)
        if partcount is not None:
            manifest.part_count = int(partcount)
            if len(manifest.image_parts) != manifest.part_count:
                raise ValueError(
                    'Part count {0} does not equal parts found:{1}'
                    .format(len(manifest.image_parts)), manifest.part_count)
        else:
            manifest.part_count = len(manifest.image_parts)
        for index, part in enumerate(manifest.image_parts):
            if part is None:
                raise ValueError('part {0} must not be None'.format(index))
        return manifest

    def __repr__(self):
        buf = ""
        for key in self.__dict__:
                buf += "\n" + str(key) + " -->: " + str(self.__dict__[key])
        return buf
