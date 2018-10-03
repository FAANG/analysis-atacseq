#!/usr/bin/env python

#######################################################################
#######################################################################
## Created on August 6th 2018 to create QC metrics file
#######################################################################
#######################################################################

import os
import argparse

import funcs

############################################
############################################
## PARSE ARGUMENTS
############################################
############################################

Description = 'Create a tab-delimited file with various QC metrics generated by BABS-ATACSeqPE pipeline. This will be specific to directory structure of BABS-ATACSeqPE nextflow pipeline.'
Epilog = """Example usage: python pipeline_qc_to_tsv.py <RESULTS_DIR> <OUT_FILE> <MITO_NAME>"""
argParser = argparse.ArgumentParser(description=Description, epilog=Epilog)

## REQUIRED PARAMETERS
argParser.add_argument('RESULTS_DIR', help="Results directory. The directory structure used to find files will be specific to BABS-ATACSeqPE nextflow pipeline.")
argParser.add_argument('OUT_FILE', help="Path to output file.")
argParser.add_argument('MITO_NAME', help="Name of Mitochondrial chomosome in genome fasta (e.g. chrM).")

args = argParser.parse_args()

############################################
############################################
## MAIN FUNCTION
############################################
############################################

def pipeline_qc_to_tsv(ResultsDir,MitoName,OutFile):

    funcs.makedir(os.path.dirname(OutFile))

    fileInfoList = [('RUN-LEVEL', 'cutadapt', '', ResultsDir, '.cutadapt.log'),
                    ('RUN-LEVEL', 'flagstat', 'unfiltered', ResultsDir, '.mkD.sorted.bam.flagstat'),
                    ('RUN-LEVEL', 'idxstats', 'unfiltered', ResultsDir, '.mkD.sorted.bam.idxstats'),
                    ('RUN-LEVEL', 'picard_insert_metrics', 'unfiltered', ResultsDir, '.mkD.CollectMultipleMetrics.insert_size_metrics'),
                    ('RUN-LEVEL', 'flagstat', 'filter', ResultsDir, '.clN.sorted.bam.flagstat'),
                    ('RUN-LEVEL', 'idxstats', 'filter', ResultsDir, '.clN.sorted.bam.idxstats'),

                    ('REPLICATE-LEVEL', 'flagstat', '', os.path.join(ResultsDir,'align/replicateLevel/'), '.RpL.rmD.sorted.bam.flagstat'),
                    ('REPLICATE-LEVEL', 'macs2', '', os.path.join(ResultsDir,'align/replicateLevel/'), '_peaks.broadPeak'),
                    ('REPLICATE-LEVEL', 'frip', '', os.path.join(ResultsDir,'align/replicateLevel/'), '_peaks.frip.txt'),

                    ('SAMPLE-LEVEL', 'flagstat', '', os.path.join(ResultsDir,'align/sampleLevel/'), '.SmL.rmD.sorted.bam.flagstat'),
                    ('SAMPLE-LEVEL', 'macs2', '', os.path.join(ResultsDir,'align/sampleLevel/'), '_peaks.broadPeak'),
                    ('SAMPLE-LEVEL', 'frip', '', os.path.join(ResultsDir,'align/sampleLevel/'), '_peaks.frip.txt')]

    headerDict = {}
    qcDict = {}
    for section,tool,header_prefix,search_dir,extension in fileInfoList:
        fileList = funcs.recursive_glob(search_dir, '*%s' % (extension))

        if not qcDict.has_key(section):
            qcDict[section] = {}
        if not headerDict.has_key(section):
            headerDict[section] = []

        for idx in range(len(fileList)):
            sample = os.path.basename(fileList[idx])[:-len(extension)]
            if not qcDict[section].has_key(sample):
                qcDict[section][sample] = []

            if tool == 'cutadapt':
                fields = ['totalPairs','passTrimmedPairs','passTrimmedBases']
                ofields = fields
                cutadaptDict = funcs.cutadaptPELogToDict(fileList[idx])
                qcDict[section][sample] += [str(cutadaptDict[x]) for x in fields]
                if idx == 0:
                    headerDict[section] += [header_prefix+' '+x for x in ofields]

            elif tool == 'flagstat':
                fields = ['in total','mapped','properly paired','duplicates','read1','read2']
                ofields = ['totalPairs','mapped','properlyPaired','duplicates','read1','read2']
                flagstatDict = funcs.flagstatToDict(fileList[idx])
                for field in fields:
                    if field in ['in total']:
                        qcDict[section][sample] += ['%s' % (flagstatDict[field][0]/2)]
                    else:
                        qcDict[section][sample] += ['%s' % (funcs.percentToStr(flagstatDict[field][0],flagstatDict['in total'][0],sigFigs=2,parentheses=False))]
                if idx == 0:
                    headerDict[section] += [header_prefix+' '+x for x in ofields]

            elif tool == 'idxstats':
                fields = [MitoName]
                ofields = fields
                idxstatsDict = funcs.idxstatsToDict(fileList[idx])
                if MitoName in idxstatsDict.keys():
                    sumCount = sum([x[1] for x in idxstatsDict.values()])
                    for field in fields:
                        qcDict[section][sample] += ['%s' % (funcs.percentToStr(idxstatsDict[field][1],sumCount,sigFigs=2,parentheses=False))]
                    if idx == 0:
                        headerDict[section] += [header_prefix+' '+x for x in ofields]

            elif tool == 'picard_insert_metrics':
                fields = ['MEAN_INSERT_SIZE', 'STANDARD_DEVIATION', 'MAX_INSERT_SIZE']
                ofields = ['insertMean', 'insertStdDev', 'insertMax']
                metricsDict = funcs.picardInsertMetricsToDict(fileList[idx])
                qcDict[section][sample] += [metricsDict[x] for x in fields]
                if idx == 0:
                    headerDict[section] += [header_prefix+' '+x for x in ofields]

            elif tool == 'macs2':
                fields = ['numPeaks']
                ofields = fields
                numLines = str(funcs.numLinesInFile(fileList[idx]))
                qcDict[section][sample] += [numLines]
                if idx == 0:
                    headerDict[section] += [header_prefix+' '+x for x in ofields]

            elif tool == 'frip':
                fields = ['fripScore']
                ofields = fields
                fin = open(fileList[idx],'r')
                frip = fin.readline().strip()
                fin.close()
                qcDict[section][sample] += [frip]
                if idx == 0:
                    headerDict[section] += [header_prefix+' '+x for x in ofields]

    sectionOrder = ['RUN-LEVEL', 'REPLICATE-LEVEL', 'SAMPLE-LEVEL']
    fout = open(OutFile,'w')
    for section in sectionOrder:
        if len(qcDict[section]) != 0:
            fout.write('## %s\n' % (section))
            fout.write('\t'.join(['sample'] + headerDict[section]) + '\n')
            for sample in sorted(qcDict[section].keys()):
                fout.write('\t'.join([sample] + qcDict[section][sample]) + '\n')
            fout.write('\n')
    fout.close()

############################################
############################################
## RUN FUNCTION
############################################
############################################

pipeline_qc_to_tsv(ResultsDir=args.RESULTS_DIR,MitoName=args.MITO_NAME,OutFile=args.OUT_FILE)

############################################
############################################
############################################
############################################
