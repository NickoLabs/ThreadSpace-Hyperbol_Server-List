<?php
function dynamic_multisort($array_to_sort, $arrFields, $arrDirection)
{
	/**
	* @desc You really should validate the posted sort direction against a list of valid possibilities.
	*         Options are SORT_ASC, SORT_DESC, etc, as shown in the documentation for array_multisort
	*		  This doesn't account for a need to sort by multiple columns at once, but could be modified 
	*		   for that purpose.
	*/
	/*$sort['direction'] = $arrDirection ; //'SORT_ASC';
	$sort['field']     = $arrFields; //'ORDER';*/
	
	/*   
	$array_to_sort['TestCase1'] = array('name'=>'Test1','value'=>'218');
	$array_to_sort['TestCase2'] = array('name'=>'Test2','value'=>'10');
	$array_to_sort['TestCase3'] = array('name'=>'Test3','value'=>'64');
	*/
	
	/**
	* @desc Build columns using the values, for sorting in php
	*/
	$sort_arr = array();
	foreach($array_to_sort AS $uniqid => $row)
	{
		foreach($row AS $key=>$value)
		{
			$sort_arr[$key][$uniqid] = $value;
		}
	}
	
	/* Debug : 
	print '<b>Before sorting</b>: <br> <pre>';
	print_r($array_to_sort);
	print '</pre>';
	//*/
	
	//
	// Vérifie que les deux array ont la même quantité d'informations
	//
	if (count($arrDirection) == count($arrFields))
	{
		$stringOfArrayToSort = "array_multisort(";
		
		for ($x = 0; $x < count($arrDirection); $x++)
		{
			$stringOfArrayToSort .= '$sort_arr["' . $arrFields[$x] . '"], constant("' . $arrDirection[$x] . '"), ';
		}
		
		//
		// Retire la virgule supplémentaire
		//
		$stringOfArrayToSort = substr($stringOfArrayToSort, 0, strlen($stringOfArrayToSort)-2);
		$stringOfArrayToSort .= ', $array_to_sort);';
		
		eval($stringOfArrayToSort);	//array_multisort($sort_arr['ORDER'], constant('SORT_ASC'), $sort_arr['PRIX_DEMANDE'], constant('SORT_ASC'), $array_to_sort);
	}
	/* Debug : 
	print '<b>After sorting</b>: <br> <pre>';
	print_r($array_to_sort);
	print '</pre>';
	//*/
	return $array_to_sort;
} ?>