#!/usr/bin/env python

__author__ = "Kishori M Konwar"
__copyright__ = "Copyright 2013, MetaPathways"
__credits__ = ["r"]
__version__ = "1.0"
__maintainer__ = "Kishori M Konwar"
__status__ = "Release"


"""Contains general utility code for the metapaths project"""

try:
    import os, re

    from shutil import rmtree
    from optparse import make_option
    from os import path, _exit

    from libs.python_modules.utils.metapathways_utils import *
    from libs.python_modules.utils.sysutil import pathDelim
    from libs.python_modules.utils.utils import *
    from libs.python_modules.pipeline.context import *
except:
    print "Cannot load some modules"
    sys.exit(0)
   
PATHDELIM = pathDelim()


class JobCreator():
      """ This class looks up the steps status redo, yes, skip and decided which steps 
          needs to be added into the job/context list """ 

      params = {}
      configs = {}

      stagesInOrder = []
      def  __init__(self, params, configs):
          self.params = params
          self.configs = configs
          #print self.configs

      def addJobs(self, s):
          contextCreator = ContextCreator(self.params, self.configs)

          for stage in contextCreator.getStageList():
              if stage in self.params['metapaths_steps']:
                 contexts = contextCreator.getContexts(s, stage)
                 s.addContexts(contexts) 
                  



@Singleton
class Params:
      params  = {}
      def __init__(self, params):
          self.params = params
          pass

      def get(self, key1, key2 = None, default = None):
          if not key1 in self.params:
              return default

          if key2 == None:
             return self.params[key1]
          
          if not key2 in self.params[key1]:
              return default

          return self.params[key1][key2]

@Singleton
class Configs:

      configs = None 
      def __init__(self, configs):
         for key, value in configs.iteritems():  
             setattr(self, key, value)


@Singleton
class ContextCreator:
      params = None
      configs = None
      factory = {}
      stageList = []

      def _Message(self, str):

          return '{0: <60}'.format(str)

      def create_quality_check_cmd(self, s):
          """ PREPROCESS_INPUT """
          contexts = []
         
          '''inputs'''
          input_file = s.input_file 


          '''outputs'''
          output_fas = s.preprocessed_dir + PATHDELIM + s.sample_name + ".fasta"
          mapping_file =  s.preprocessed_dir + PATHDELIM + s.sample_name + ".mapping.txt"
          nuc_stats_file = s.output_run_statistics_dir + PATHDELIM + s.sample_name + ".nuc.stats" 
          contig_lengths_file = s.output_run_statistics_dir + PATHDELIM + s.sample_name + ".contig.lengths.txt"

          '''params'''
          min_length =   self.params.get('quality_control','min_length', default = '180')
          type = 'nucleotide'

          context = Context()
          context.name = 'PREPROCESS_INPUT'
          context.inputs = { 'input_file' : input_file }

          context.outputs = { 
                              'output_fas': output_fas, 'mapping_file': mapping_file,\
                              'nuc_stats_file' : nuc_stats_file, 'contig_lengths_file' : contig_lengths_file\
                            }
          context.status = self.params.get('metapaths_steps','PREPROCESS_INPUT')


          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.PREPROCESS_INPUT

          cmd = "%s --min_length %d --log_file %s  -i %s -o  %s -M %s -t %s -L %s"\
               %( pyScript, float(min_length), context.outputs['nuc_stats_file'], context.inputs['input_file'], 
                  context.outputs['output_fas'], context.outputs['mapping_file'],\
                   type, context.outputs['contig_lengths_file']\
                 )

          context.message = self._Message("PREPROCESSING THE INPUT")
          context.commands = [cmd]
          contexts.append(context)
          return contexts


      def create_orf_prediction_cmd(self, s) :
          """ ORF_PREDICTION """
          contexts = []
         
          '''inputs'''
          input_file = s.preprocessed_dir + PATHDELIM + s.sample_name + ".fasta"

          '''outputs'''
          output_gff = s.orf_prediction_dir + s.sample_name + ".gff"

          context = Context()
          context.name = 'ORF_PREDICTION'
          context.inputs = { 'input_file' : input_file }
          context.outputs = { 'output_gff' : output_gff }
          context.status = self.params.get('metapaths_steps','ORF_PREDICTION')

          options = " -m -p meta -f gff"

          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.ORF_PREDICTION
          
          cmd = "%s %s -i %s -o %s" %( pyScript, options, context.inputs['input_file'],\
                context.outputs['output_gff'] ) 

          context.commands = [cmd]
          context.message = self._Message("ORF PREDICTION")
          contexts.append(context)
          return contexts

      def create_aa_orf_sequences_cmd(self, s):
         """ ORF_TO_AMINO """
         contexts = []

         ''' inputs '''
         input_gff = s.orf_prediction_dir + s.sample_name + ".gff"
         input_fasta = s.preprocessed_dir + PATHDELIM + s.sample_name + ".fasta"

         '''outputs'''
         output_faa = s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".faa"
         output_fna = s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".fna"
         output_gff = s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".unannot.gff"

         context = Context()
         context.name = 'ORF_TO_AMINO'
         context.inputs = { 'input_gff' : input_gff, 'input_fasta': input_fasta }
         context.outputs = { 'output_faa': output_faa, 'output_fna': output_fna, 'output_gff' : output_gff }
         context.status = self.params.get('metapaths_steps','ORF_TO_AMINO')

         pyScript = self.configs.METAPATHWAYS_PATH + self.configs.ORF_TO_AMINO 
         cmd = "%s -g  %s  -n %s --output_nuc %s --output_amino %s --output_gff %s"\
                %(pyScript, context.inputs['input_gff'], context.inputs['input_fasta'],\
                  context.outputs['output_fna'], context.outputs['output_faa'],\
                  context.outputs['output_gff'])

         context.message = self._Message("CREATING AMINO ACID SEQS FROM GFF FILE")
         context.commands = [cmd]
         contexts.append(context)
         return contexts


      def create_create_filtered_amino_acid_sequences_cmd(self, s):
          """FILTER_AMINOS"""
          contexts = []

          '''inputs'''
          input_faa = s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".faa"


          '''outputs'''
          output_filtered_faa = s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".qced.faa"
          amino_stats_file = s.output_run_statistics_dir + PATHDELIM + s.sample_name + ".amino.stats"
          orf_lengths_file = s.output_run_statistics_dir + PATHDELIM + s.sample_name + ".orf.lengths.txt"

          '''params'''
          min_length = self.params.get('orf_prediction', 'min_length', default=60)
          type = 'amino'

          context = Context()
          context.name = 'FILTER_AMINOS'
          context.inputs = { 'input_faa' : input_faa }
          context.outputs = { 'output_filtered_faa': output_filtered_faa,\
                              'amino_stats_file': amino_stats_file,\
                              'orf_lengths_file': orf_lengths_file }

          context.status = self.params.get('metapaths_steps','FILTER_AMINOS')

          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.PREPROCESS_INPUT

          cmd = "%s  --min_length %s --log_file %s  -i %s -o  %s -L %s -t %s"\
                %( pyScript, min_length, context.outputs['amino_stats_file'],\
                 context.inputs['input_faa'],  context.outputs['output_filtered_faa'],\
                 context.outputs['orf_lengths_file'], type)

          context.commands = [cmd]
          print cmd
          context.message = self._Message("FILTER AMINO ACID SEQS")
          contexts.append(context)
          return contexts



      def create_refscores_compute_cmd(self, s):
          """COMPUTE_REFSCORES"""
          contexts = []

          '''inputs'''
          input_filtered_faa = s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".qced.faa"

          '''outputs'''
          output_refscores =  s.blast_results_dir + PATHDELIM + s.sample_name + ".refscores" + "." + s.algorithm

          context = Context()
          context.name = 'COMPUTE_REFSCORES'
          context.inputs = { 'input_filtered_faa' : input_filtered_faa }
          context.outputs = { 'output_refscores': output_refscores}

          context.status = self.params.get('metapaths_steps','COMPUTE_REFSCORES')

          cmd = None
          if s.algorithm == 'BLAST':
              pyScript      = self.configs.METAPATHWAYS_PATH + self.configs.COMPUTE_REFSCORES
              formatterExec =  self.configs.METAPATHWAYS_PATH + self.configs.FORMATDB_EXECUTABLE
              searchExec =   self.configs.METAPATHWAYS_PATH + self.configs.BLASTP_EXECUTABLE
              cmd = "%s  -F %s -B %s -o %s -i %s -a  %s"\
                   %( pyScript, formatterExec, searchExec, output_refscores, input_filtered_faa, s.algorithm)

          elif s.algorithm == 'LAST':
              pyScript      = self.configs.METAPATHWAYS_PATH + self.configs.COMPUTE_REFSCORES
              formatterExec =  self.configs.METAPATHWAYS_PATH + self.configs.LASTDB_EXECUTABLE
              searchExec =   self.configs.METAPATHWAYS_PATH + self.configs.LAST_EXECUTABLE
              cmd = "%s  -F %s -B %s -o %s -i %s -a %s"\
                       %( pyScript, formatterExec, searchExec, output_refscores, input_filtered_faa, s.algorithm)
   
          context.commands = [ cmd ]
          context.message = self._Message("COMPUTING REFSCORES FOR BITSCORE")
          contexts.append(context)
          return contexts
             
        
      def create_blastp_against_refdb_cmd(self, s):
          """FUNC_SEARCH"""
          contexts = []
      
          '''parameters'''

          max_evalue = self.params.get('annotation', 'max_evalue', default=0.000001)
          max_hits =  self.params.get('annotation', 'max_hits', default=5)
      
          dbstring =  self.params.get('annotation', 'dbs', default=None)
          dbs= [x.strip() for x in dbstring.split(",")  if len(x)!=0 ]
      
          
          for db in dbs:
              '''inputs'''
              input_filtered_faa = s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".qced.faa"
      
              '''outputs'''
              blastoutput = s.blast_results_dir + PATHDELIM + s.sample_name + "." + db + "." + s.algorithm + "out"
      
              refDbFullName = self.configs.REFDBS + PATHDELIM + 'functional'+ PATHDELIM +\
                              'formatted' + PATHDELIM + db 

              context = Context()
              context.name = 'FUNC_SEARCH:' +db
              context.inputs = { 'input_filtered_faa' : input_filtered_faa }
              context.outputs = { 'blastoutput': blastoutput}
      
              cmd = None
              if s.algorithm == 'BLAST':
                 searchExec =   self.configs.METAPATHWAYS_PATH + self.configs.BLASTP_EXECUTABLE
                 cmd="%s -num_threads 16  -max_target_seqs %s  -outfmt 6  -db %s -query  %s -evalue  %s  -out %s"\
                      %( searchExec, max_hits, refDbFullName, context.inputs['input_filtered_faa'],\
                        max_evalue, context.outputs['blastoutput']) 
                 context.message = self._Message("BLASTING AMINO SEQS AGAINST " + db)
   
              if s.algorithm == 'LAST':
                  searchExec =   self.configs.METAPATHWAYS_PATH + self.configs.LAST_EXECUTABLE
                  cmd="%s -o %s -f 0 %s %s"\
                       %( searchExec, blastoutput, refDbFullName, input_filtered_faa) 
                  context.message = self._Message("LASTING AMINO SEQS AGAINST " + db)
              
              context.status = self.params.get('metapaths_steps','FUNC_SEARCH')
              context.commands = [ cmd ]

              print cmd
              contexts.append(context)

          return contexts
          

      def create_parse_blast_cmd(self, s ):
          """  Command for parsing the blast flie snd create the parse blast files
            input -- blastoutput
            output -- parseed files
            refscorefile   -- refscore file
            min_bsr   -- minimum bsr ratio for accepting into annotation
            max_evalue  -- max evalue
            min_score   -- min score
            min_length  -- min_length in amino acids, typcically 100 amino acids.ould be minimum
          """
          """PARSE_FUNC_SEARCH"""
          contexts = []

          '''parameters'''
          min_bsr    = self.params.get('annotation', 'min_bsr', default=0.4)
          min_score  = self.params.get('annotation', 'min_score', default=0.0)
          min_length = self.params.get('annotation', 'min_length', default=100)
          max_evalue = self.params.get('annotation', 'max_evalue', default=1000)
          dbstring =   self.params.get('annotation', 'dbs', default=None)
          dbs= [x.strip() for x in dbstring.split(",")  if len(x)!=0 ]
      
          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.PARSE_FUNC_SEARCH
          for db in dbs:
             '''inputs'''
             input_db_blastout = s.blast_results_dir + PATHDELIM + s.sample_name + "." + db + "." + s.algorithm+"out"
             refscorefile = s.blast_results_dir + PATHDELIM + s.sample_name +\
                            ".refscores" +"." + s.algorithm
             dbmapFile = self.configs.REFDBS + PATHDELIM + 'functional' + PATHDELIM + 'formatted'\
                         + PATHDELIM + db + "-names.txt"

             '''outputs'''
             output_db_blast_parse = s.blast_results_dir + PATHDELIM + s.sample_name +\
                                     "." + db + "." + s.algorithm+"out.parsed.txt"

             context = Context()
             context.name = 'PARSE_FUNC_SEARCH:' + db
             context.inputs = { 'input_db_blastout' : input_db_blastout,\
                                'dbmapFile': dbmapFile,\
                                'refscorefile': refscorefile 
                               }

             context.outputs = { 'output_db_blast_parse':output_db_blast_parse}

             cmd="%s -d %s  -b %s -m %s  -r  %s  --min_bsr %s  --min_score %s --min_length %s --max_evalue %s"\
                   %( pyScript, db, context.inputs['input_db_blastout'],\
                   context.inputs['dbmapFile'],  context.inputs['refscorefile'],\
                   min_bsr, min_score, min_length, max_evalue)
      
             if s.algorithm == 'LAST':
                 cmd = cmd + ' --algorithm LAST'
      
             if s.algorithm == 'BLAST':
                  cmd = cmd + ' --algorithm BLAST'
             context.commands = [ cmd ]
             context.status = self.params.get('metapaths_steps','PARSE_FUNC_SEARCH')
             context.message = self._Message("PARSING " + s.algorithm + " OUTPUT FOR " + db)
             contexts.append(context)

          return contexts
      

      def create_scan_rRNA_seqs_cmd(self, s):
          """SCAN_rRNA"""
          contexts = []

          '''parameters'''
          bscore_cutoff = self.params.get('rRNA', 'min_bitscore', default=27)
          eval_cutoff =   self.params.get( 'rRNA', 'max_evalue', default=6)
          identity_cutoff = self.params.get('rRNA', 'min_identity', default=40)
          dbstring = self.params.get('rRNA', 'refdbs', default=None)
          refrRNArefDBs= [ x.strip() for x in dbstring.split(',') if len(x.strip()) ]

          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.PARSE_FUNC_SEARCH

          '''inputs'''
          input_fasta = s.preprocessed_dir +  PATHDELIM + s.sample_name + ".fasta"

          pyScript =  self.configs.METAPATHWAYS_PATH + self.configs.BLASTN_EXECUTABLE
          executable= self.configs.METAPATHWAYS_PATH + self.configs.SCAN_rRNA

          for db in refrRNArefDBs:
             '''inputs'''
             dbpath = self.configs.REFDBS + PATHDELIM + 'taxonomic' + PATHDELIM + 'formatted' + PATHDELIM + db
             dbsequences = self.configs.REFDBS + PATHDELIM + "taxonomic" + PATHDELIM+  db

             '''outputs'''
             rRNA_blastout = s.blast_results_dir + PATHDELIM + s.sample_name + ".rRNA." + db + ".BLASTout"
             rRNA_stat_results= s.output_results_rRNA_dir + s.sample_name + "." + db + ".rRNA.stats.txt"

             context = Context()
             context.name = 'SCAN_rRNA:' + db
             context.inputs = {  'input_fasta':input_fasta, 'dbsequences':dbsequences }
             context.inputs1 = { 'dbpath' : dbpath }
             context.outputs = { 'rRNA_blastout':rRNA_blastout, 'rRNA_stat_results': rRNA_stat_results }

             cmd1="%s -outfmt 6 -num_threads 8  -query %s -out %s -db %s -max_target_seqs 5"\
                   %(pyScript, context.inputs['input_fasta'], context.outputs['rRNA_blastout'], context.inputs1['dbpath'])



             """ now the scanning part"""


             cmd2= "%s -o %s -b %s -e %s -s %s"  %(executable, context.outputs['rRNA_stat_results'],\
                   bscore_cutoff, eval_cutoff, identity_cutoff)

             cmd2 = cmd2 +  " -i "  + context.outputs['rRNA_blastout'] + " -d " + context.inputs['dbsequences']
             context.commands = [ cmd2, cmd1 ]
             context.status = self.params.get('metapaths_steps','SCAN_rRNA')
             context.message = self._Message("SCANNING FOR rRNA USING DB " + db)
             contexts.append(context)


          return contexts




      def create_tRNA_scan_statistics(self, s):
           """SCAN_tRNA"""

           contexts = []

           '''inputs'''
           input_fasta = s.preprocessed_dir + PATHDELIM + s.sample_name + ".fasta"
           TPCsignal =  self.configs.METAPATHWAYS_PATH + self.configs.RESOURCES_DIR+ PATHDELIM + 'TPCsignal'
           Dsignal =  self.configs.METAPATHWAYS_PATH + self.configs.RESOURCES_DIR+ PATHDELIM + 'Dsignal'

           '''outputs'''
           tRNA_stats_output = s.output_results_tRNA_dir + PATHDELIM + s.sample_name +  ".tRNA.stats.txt"   
           tRNA_fasta_output = s.output_results_tRNA_dir + PATHDELIM + s.sample_name +  ".tRNA.fasta"


           context = Context()
           context.name = 'SCAN_tRNA'
           context.inputs = { 'input_fasta':input_fasta, 'TPCsignal':TPCsignal, 'Dsignal':Dsignal }
           context.outputs = { 'tRNA_stats_output':tRNA_stats_output, 'tRNA_fasta_output': tRNA_fasta_output}



           pyScript = self.configs.METAPATHWAYS_PATH + self.configs.SCAN_tRNA
           cmd= "%s -o %s -F %s  -i %s -T %s  -D %s"\
                %(pyScript, context.outputs['tRNA_stats_output'], context.outputs['tRNA_fasta_output'],\
                context.inputs['input_fasta'], context.inputs['TPCsignal'], context.inputs['Dsignal'])

           context.commands = [ cmd ]
           context.status = self.params.get('metapaths_steps','SCAN_tRNA')
           context.message = self._Message("SCANNING FOR tRNA USING tRNA-Scan")
           contexts.append(context)
           return contexts


      def create_annotate_genebank_cmd(self, s ):
          """ANNOTATE ORFS"""
          contexts = []

          '''inputs'''
          input_unannotated_gff = s.orf_prediction_dir +PATHDELIM + s.sample_name+".unannot.gff"
          mapping_txt =  s.preprocessed_dir + PATHDELIM + s.sample_name + ".mapping.txt" 

          '''outputs'''
          output_annotated_gff  = s.genbank_dir +PATHDELIM + s.sample_name+".annot.gff"
          output_comparative_annotation  =  s.output_results_annotation_table_dir\
                                              + PATHDELIM + s.sample_name
          dbstring =   self.params.get('annotation', 'dbs', default=None)
          refdbs= [x.strip() for x in dbstring.split(",")  if len(x)!=0 ]

          rRNAdbstring =   self.params.get('rRNA', 'refdbs', default=None)
          rRNAdbs= [x.strip() for x in dbstring.split(",")  if len(x)!=0 ]



          context = Context()
          context.name = 'ANNOTATE_ORFS'
        
          context.inputs = { 'mapping_txt':mapping_txt,
                             'input_unannotated_gff':input_unannotated_gff
                           }
          context.outputs = { 
                'output_annotated_gff':output_annotated_gff,
                }
          context.outputs1 = { 
                'output_comparative_annotation':output_comparative_annotation
               }


          context.status = self.params.get('metapaths_steps','ANNOTATE_ORFS')

          '''use rRNA stats if they are available'''
          options = ''
          for rRNArefdb in rRNAdbs:
               rRNA_stat_results= s.output_results_rRNA_dir + s.sample_name +\
                                  '.' + rRNArefdb + '.rRNA.stats.txt' 
               if  hasResults(rRNA_stat_results)  :
                   context.inputs['rRNA_stat_results']  = rRNA_stat_results                   
                   options += " --rRNA_16S " +  context.inputs['rRNA_stat_results'] 


          '''use rRNA stats if they are available'''
          tRNA_stat_results= s.output_results_tRNA_dir + PATHDELIM + s.sample_name + '.tRNA.stats.txt' 
          if hasResults(tRNA_stat_results): 
               context.inputs['tRNA_stat_results']  = tRNA_stat_results                   
               options += " --tRNA " +  context.inputs['tRNA_stat_results']


          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.ANNOTATE_ORFS
          cmd="%s --input_gff  %s -o %s  %s --output-comparative-annotation %s \
                    --algorithm %s "\
                %(pyScript, context.inputs['input_unannotated_gff'],\
                context.outputs['output_annotated_gff'],  options,\
                context.outputs1['output_comparative_annotation'],s.algorithm )

          for refdb in refdbs:
               parsed_file =  s.blast_results_dir + PATHDELIM + s.sample_name\
                              + "." + refdb+ "." + s.algorithm + "out.parsed.txt"
               context.inputs[parsed_file] = parsed_file
               cmd = cmd + " -b " + parsed_file + " -d " + refdb + " -w 1 "


          cmd = cmd + " -m " + context.inputs['mapping_txt']

          context.message = self._Message("ANNOTATE ORFS")
          context.commands = [ cmd ]
          contexts.append(context)
          return contexts

      def create_genbank_file_cmd(self, s): 
          """GENBANK_FILE"""

          contexts = []

          '''inputs'''
          input_annot_gff  = s.genbank_dir +PATHDELIM + s.sample_name+".annot.gff"
          input_nucleotide_fasta = s.preprocessed_dir + PATHDELIM + s.sample_name + ".fasta"
          input_amino_acid_fasta =  s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".qced.faa"

          '''outputs'''
          output_annot_gbk= s.genbank_dir + PATHDELIM + s.sample_name +  '.gbk'

          context = Context()
          context.name = 'GENBANK_FILE'
        
          context.inputs = { 
                             'input_annot_gff':input_annot_gff,
                             'input_nucleotide_fasta':input_nucleotide_fasta,
                             'input_amino_acid_fasta':input_amino_acid_fasta
                           }
          context.outputs = {
                               'output_annot_gbk': output_annot_gbk
                            }

          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.GENBANK_FILE
          cmd="%s -g %s -n %s -p %s " %(pyScript, context.inputs['input_annot_gff'],\
               context.inputs['input_nucleotide_fasta'], context.inputs['input_amino_acid_fasta'])  


          """GENBANK_FILE"""
          genbank_file_status = self.params.get('metapaths_steps','GENBANK_FILE')
          if genbank_file_status in ['redo'] or\
             (genbank_file_status in ['yes'] and not s.hasGenbankFile() ):
             cmd += ' --out-gbk ' + context.outputs['output_annot_gbk']
          context.message =  self._Message("GENBANK FILE" )

          context.status =  genbank_file_status = self.params.get('metapaths_steps','GENBANK_FILE')
          context.commands = [ cmd ]
          contexts.append(context)
          return contexts


      def create_ptinput_cmd(self, s): 
          """PATHOLOGIC_INPUT"""

          contexts = []

          '''inputs'''
          input_annot_gff  = s.genbank_dir +PATHDELIM + s.sample_name+".annot.gff"
          input_nucleotide_fasta = s.preprocessed_dir + PATHDELIM + s.sample_name + ".fasta"
          input_amino_acid_fasta =  s.orf_prediction_dir + PATHDELIM +  s.sample_name + ".qced.faa"

          '''outputs'''

          context = Context()
          context.name = 'PATHOLOGIC_INPUT'
        
          context.inputs = { 
                             'input_annot_gff':input_annot_gff,
                             'input_nucleotide_fasta':input_nucleotide_fasta,
                             'input_amino_acid_fasta':input_amino_acid_fasta
                           }
          context.outputs = {
                               'output_fasta_pf_dir':s.output_fasta_pf_dir
                            }

          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.GENBANK_FILE
          cmd="%s -g %s -n %s -p %s " %(pyScript, context.inputs['input_annot_gff'],\
               context.inputs['input_nucleotide_fasta'], context.inputs['input_amino_acid_fasta'])  


          """PATHOLOGIC_INPUT"""
          ptinput_status = self.params.get('metapaths_steps','PATHOLOGIC_INPUT')
          if ptinput_status in ['redo'] or ( ptinput_status in ['yes'] and not s.hasPToolsInput() ):
              cmd += ' --out-ptinput ' + context.outputs['output_fasta_pf_dir']
          context.message = self._Message("PATHOLOGIC INPUT" )

          context.status = self.params.get('metapaths_steps','PATHOLOGIC_INPUT')
          context.commands = [ cmd ]
          contexts.append(context)
          return contexts


      def create_report_files_cmd(self, s):
          """CREATE_ANNOT_REPORTS"""

          contexts = []
          '''input'''
          input_annot_gff  = s.genbank_dir +PATHDELIM + s.sample_name+ ".annot.gff"

          '''output'''
          output_annot_table = s.output_results_annotation_table_dir +\
                               PATHDELIM + 'functional_and_taxonomic_table.txt'

          
          context = Context()
          context.name = 'CREATE_ANNOT_REPORTS'
          basefun  =  self.configs.REFDBS + PATHDELIM + 'functional_categories' 
          basencbi = self.configs.REFDBS + PATHDELIM + 'ncbi_tree' 
          context.inputs = {
                            'input_annot_gff':input_annot_gff,
                           'KO_classification':basefun + PATHDELIM +  'KO_classification.txt',
                           'COG_categories':basefun + PATHDELIM +  'COG_categories.txt',
                           'SEED_subsystems':basefun + PATHDELIM + 'SEED_subsystems.txt',
                           'ncbi_taxonomy_tree': basencbi + PATHDELIM + 'ncbi_taxonomy_tree.txt'
                           }
          context.outputs = {
                           'output_results_annotation_table_dir':s.output_results_annotation_table_dir,
                           'output_annot_table':output_annot_table,
                         }


          dbstring =   self.params.get('annotation', 'dbs', default=None)
          refdbs= [x.strip() for x in dbstring.split(",")  if len(x)!=0 ]

          db_argument_string = ''
          for dbname in refdbs: 
              parsed_file =  s.blast_results_dir + PATHDELIM + s.sample_name\
                              + "." + dbname+ "." + s.algorithm + "out.parsed.txt"
              context.inputs[parsed_file] = parsed_file

              db_argument_string += ' -d ' + dbname
              db_argument_string += ' -b ' + parsed_file


          pyScript = self.configs.METAPATHWAYS_PATH + self.configs.CREATE_ANNOT_REPORTS


          cmd = "%s %s --input-annotated-gff %s  --input-kegg-maps %s \
                 --input-cog-maps %s --input-seed-maps %s --output-dir %s \
                 --ncbi-taxonomy-map %s "\
               %(\
                  pyScript, \
                  db_argument_string,\
                  context.inputs['input_annot_gff'],\
                  context.inputs['KO_classification'],\
                  context.inputs['COG_categories'],\
                  context.inputs['SEED_subsystems'],\
                  context.outputs['output_results_annotation_table_dir'],\
                  context.inputs['ncbi_taxonomy_tree']\
               )

          context.commands = [ cmd ]
          context.status = self.params.get('metapaths_steps', 'CREATE_ANNOT_REPORTS') 
          context.message = self._Message("CREATING REPORT FILE FOR ORF ANNOTATION")
          print context.status

          contexts.append(context)
          return contexts

      def create_pgdb_using_pathway_tools_cmd(self, s):
          """BUILD PGDB"""
          contexts = []

          '''input'''
          ptools_input_folder = s.output_fasta_pf_dir

          '''output'''

          context = Context()
          context.name = 'BUILD_PGDB'
          context.inputs = {
                             'ptools_input_folder':ptools_input_folder
                           }

          ptoolsExec = self.configs.PATHOLOGIC_EXECUTABLE
          cmd="%s -patho %s"  %(ptoolsExec, context.inputs['ptools_input_folder'] +  PATHDELIM)

          taxonomic_pruning_flag = self.params.get('ptools_settings', 'taxonomic_pruning')
          if taxonomic_pruning_flag=='no':
              cmd= cmd + " -no-taxonomic-pruning "
          cmd= cmd + " -no-web-cel-overview"

          context.status = self.params.get('metapaths_steps', 'BUILD_PGDB') 

          context.commands = [cmd]  
          contexts.append(context)
          context.message = self._Message("RUNNING PATHOLOGIC")
          return contexts


      def __init__(self, params, configs): 
          self.params = Singleton(Params)(params)
          self.configs = Singleton(Configs)(configs)
          self.initFactoryList()
          pass

      def getContexts(self, s, stage):
          if stage in self.stageList:
              return self.factory[stage](s)

      def getStageList(self):
           return self.stageList
           

      def initFactoryList(self):
           self.factory['PREPROCESS_INPUT'] = self.create_quality_check_cmd
           self.factory['ORF_PREDICTION'] = self.create_orf_prediction_cmd
           self.factory['ORF_TO_AMINO'] = self.create_aa_orf_sequences_cmd
           self.factory['FILTER_AMINOS'] = self.create_create_filtered_amino_acid_sequences_cmd
           self.factory['COMPUTE_REFSCORES'] = self.create_refscores_compute_cmd
           self.factory['FUNC_SEARCH'] = self.create_blastp_against_refdb_cmd
           self.factory['PARSE_FUNC_SEARCH'] = self.create_parse_blast_cmd
           self.factory['SCAN_rRNA'] = self.create_scan_rRNA_seqs_cmd
           self.factory['SCAN_tRNA'] = self.create_tRNA_scan_statistics
           self.factory['ANNOTATE_ORFS'] = self.create_annotate_genebank_cmd
           self.factory['PATHOLOGIC_INPUT'] = self.create_ptinput_cmd
           self.factory['GENBANK_FILE'] = self.create_genbank_file_cmd
           self.factory['CREATE_ANNOT_REPORTS'] = self.create_report_files_cmd
           self.factory['BUILD_PGDB'] = self.create_pgdb_using_pathway_tools_cmd
           #self.factory['COMPUTE_RPKM'] = self.create_pgdb_using_pathway_tools_cmd

           self.stageList = [
                              'PREPROCESS_INPUT',
                              'ORF_PREDICTION',
                              'ORF_TO_AMINO',
                              'FILTER_AMINOS',
                              'COMPUTE_REFSCORES',
                              'FUNC_SEARCH',
                              'PARSE_FUNC_SEARCH',
                              'SCAN_rRNA',
                              'SCAN_tRNA',
                              'ANNOTATE_ORFS',
                              'PATHOLOGIC_INPUT',
                              'GENBANK_FILE',  
                              'CREATE_ANNOT_REPORTS',
#                              'MLTREEMAP_CALCULATION',
#                              'MLTREEMAP_IMAGEMAKER',
                              'BUILD_PGDB'
                           #   'COMPUTE_RPKM'
                             ]
           

       
