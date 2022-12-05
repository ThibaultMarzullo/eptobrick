# *******************************************************************************
# OpenStudio(R), Copyright (c) 2008-2021, Alliance for Sustainable Energy, LLC.
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# (1) Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# (2) Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# (3) Neither the name of the copyright holder nor the names of any contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission from the respective party.
#
# (4) Other than as required in clauses (1) and (2), distributions in any form
# of modifications or other derivative works may not use the "OpenStudio"
# trademark, "OS", "os", or any other confusingly similar designation without
# specific prior written permission from Alliance for Sustainable Energy, LLC.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER(S) AND ANY CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER(S), ANY CONTRIBUTORS, THE
# UNITED STATES GOVERNMENT, OR THE UNITED STATES DEPARTMENT OF ENERGY, NOR ANY OF
# THEIR EMPLOYEES, BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# *******************************************************************************

# Start the measure
class AlfalfaBRICK < OpenStudio::Measure::ModelMeasure
  require 'openstudio-standards'
  require 'rdf/rdfxml'
  require 'rdf/turtle'
  require 'sparql/client'

  # Define the name of the Measure.
  def name
    return 'Add I/O for alfalfa from BRICK'
  end

  # Human readable description
  def description
    return 'This measure exposes model actuators and sensors to alfalfa based on a BRICK input file'
  end

  # Human readable description of modeling approach
  def modeler_description
    return ''
  end

  # Define the arguments that the user will input.
  def arguments(model)
    args = OpenStudio::Measure::OSArgumentVector.new

    #TODO

    return args
  end

  def find_points(ttlpath)
    

    graph = RDF::Graph.load(ttlpath, format:  :ttl)
    sparql = SPARQL::Client.new(graph)
    query = sparql.select.where([nil, nil, nil])
    query.each_solution do |solution|
      solution.to_h.each do |key, value|
        newstr = value.to_s.split('#')[-1].gsub('&58', ':').gsub('&20', ' ')
        if key.to_s == "g5120" and (newstr.include? "_Sensor" or newstr.include? "_Setpoint")
          newstr = newstr.gsub("_Sensor", "").gsub("_Setpoint", "")
        end
      end

    end


  end

  def create_output(model, var, key, name, freq)
    # create reporting output variable
    new_var = OpenStudio::Model::OutputVariable.new(
      var, # from variable dictionary (eplusout.rdd)
      model
    )
    new_var.setName(name)
    new_var.setReportingFrequency(freq) # Detailed, Timestep, Hourly, Daily, Monthly, RunPeriod, Annual
    new_var.setKeyValue(key) # from variable dictionary (eplusout.rdd)
    new_var.setExportToBCVTB(true)

  end

  def create_input(workspace, name, freq)

    # create global variable
    global_var = OpenStudio::Model::EnergyManagementSystemGlobalVariable.new(
      model,
      name.gsub(' ', '')
    )
    global_var.setExportToBCVTB(true)
  
    # create EMS output variable of global variable
    ems_out_var = OpenStudio::Model::EnergyManagementSystemOutputVariable.new(
      model,
      global_var
    )
    ems_out_var.setName(name + '_EMS_Value')
    ems_out_var.setUpdateFrequency('SystemTimestep')
  
    # create reporting output variable of EMS output variable of global variable
    global_out_var = OpenStudio::Model::OutputVariable.new(
      ems_out_var.nameString(),
      model
    )
    global_out_var.setName(name + '_Value')
    global_out_var.setReportingFrequency(freq) # Detailed, Timestep, Hourly, Daily, Monthly, RunPeriod, Annual
    global_out_var.setKeyValue('EMS')
    global_out_var.setExportToBCVTB(true)
  
    # create enable of global variable
    global_var_enable = OpenStudio::Model::EnergyManagementSystemGlobalVariable.new(
      model,
      name.gsub(' ', '') + "_Enable"
    )
    global_var_enable.setExportToBCVTB(true)
  
    # create EMS output variable of enable global variable
    ems_out_var_enable = OpenStudio::Model::EnergyManagementSystemOutputVariable.new(
      model,
      global_var_enable
    )
    ems_out_var_enable.setName(name + '_Enable_EMS_Value')
    ems_out_var_enable.setUpdateFrequency('SystemTimestep')
  
    # create reporting output variable of EMS output variable of enable global variable
    global_out_var_enable = OpenStudio::Model::OutputVariable.new(
      ems_out_var_enable.nameString(),
      model
    )
    global_out_var_enable.setName(name + '_Enable_Value')
    global_out_var_enable.setReportingFrequency(freq) # Detailed, Timestep, Hourly, Daily, Monthly, RunPeriod, Annual
    global_out_var_enable.setKeyValue('EMS')
    global_out_var_enable.setExportToBCVTB(true)

    # add actuator

    act_node = model.getNodesByName(name, false)
    puts act_node
    act = OpenStudio::Model::EnergyManagementSystemActuator.new(
      act_node,
      "System Node Setpoint",
      "Temperature Setpoint"
      )

    # add EMS override and enable programs
    ov_prgm = OpenStudio::Model::EnergyManagementSystemProgram.new(model)
    ov_prgm.setName('Override_' + name)
    ov_prgm.addLine("IF #{name + '_Enable'} == 1")
    ov_prgm.addLine("SET #{name + '_Actuator'} = #{name + '_EMS_Value'}")
    ov_prgm.addLine("ELSE,")
    ov_prgm.addLine("SET #{name + '_Actuator'} = NULL")
    ov_prgm.addLine("ENDIF,")

    en_prgm = OpenStudio::Model::EnergyManagementSystemProgram.new(model)
    en_prgm.setName('Enable_' + name)
    en_prgm.addLine("SET #{name + '_Enable'} = #{name + '_Enable_EMS_Value'}")

    # add EMS program calling managers
    ov_prgm_mngr = OpenStudio::Model::EnergyManagementSystemProgramCallingManager.new(model)
    ov_prgm_mngr.setName('Override_' + name)
    ov_prgm_mngr.setCallingPoint('BeginTimestepBeforePredictor')
    ov_prgm_mngr.addProgram(ov_prgm)

    en_prgm_mngr = OpenStudio::Model::EnergyManagementSystemProgramCallingManager.new(model)
    en_prgm_mngr.setName('Enable_' + name)
    en_prgm_mngr.setCallingPoint('BeginTimestepBeforePredictor')
    en_prgm_mngr.addProgram(en_prgm)

  end

  # Define what happens when the measure is run.
  def run(model, runner, user_arguments)
    super(model, runner, user_arguments)

    # Use the built-in error checking
    if !runner.validateUserArguments(arguments(model), user_arguments)
      return false
    end

    
    
    

    log_msgs
    reset_log

    return true
  end # end the run method

  # Get all the log messages and put into output
  # for users to see.
  def log_msgs
    @msg_log.logMessages.each do |msg|
      # DLM: you can filter on log channel here for now
      if /openstudio.*/.match(msg.logChannel) # /openstudio\.model\..*/
        # Skip certain messages that are irrelevant/misleading
        next if msg.logMessage.include?('Skipping layer') || # Annoying/bogus "Skipping layer" warnings
                msg.logChannel.include?('runmanager') || # RunManager messages
                msg.logChannel.include?('setFileExtension') || # .ddy extension unexpected
                msg.logChannel.include?('Translator') || # Forward translator and geometry translator
                msg.logMessage.include?('UseWeatherFile') # 'UseWeatherFile' is not yet a supported option for YearDescription

        # Report the message in the correct way
        if msg.logLevel == OpenStudio::Info
          @runner.registerInfo(msg.logMessage)
        elsif msg.logLevel == OpenStudio::Warn
          @runner.registerWarning("[#{msg.logChannel}] #{msg.logMessage}")
        elsif msg.logLevel == OpenStudio::Error
          @runner.registerError("[#{msg.logChannel}] #{msg.logMessage}")
        elsif msg.logLevel == OpenStudio::Debug && @debug
          @runner.registerInfo("DEBUG - #{msg.logMessage}")
        end
      end
    end
    @runner.registerInfo("Total Time = #{(Time.new - @start_time).round}sec.")
  end
end # end the measure

# this allows the measure to be use by the application
AlfalfaBRICK.new.registerWithApplication
